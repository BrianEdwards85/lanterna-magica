import asyncio
import copy
import logging
import re
from typing import Any

from lanterna_magica.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Matches a single path segment:  .key  or  [index]  or  [index].key ...
_SEGMENT_RE = re.compile(r'\.([^.\[]+)|\[(\d+)\]')


def _set_path(root: dict | list, jsonpath: str, value: Any) -> None:
    """Mutate root in-place, setting the node at jsonpath to value.

    jsonpath must start with '$' followed by segments in the form
    `.key` or `[index]` (matching the output of find_sentinel_paths).
    """
    # Strip leading '$'
    remainder = jsonpath[1:]
    segments = _SEGMENT_RE.findall(remainder)
    # segments is a list of (key, index) tuples; one of each pair is empty str
    node = root
    for key, idx in segments[:-1]:
        node = node[key] if key else node[int(idx)]
    # Set the final segment
    last_key, last_idx = segments[-1]
    if last_key:
        node[last_key] = value
    else:
        node[int(last_idx)] = value


class ConfigurationOrchestrator:
    def __init__(
        self,
        configurations,
        shared_values,
        dimension_types=None,
        dimensions=None,
        slug_dimension_type_name: str = "",
    ):
        self._configurations = configurations
        self._shared_values = shared_values
        self._dimension_types = dimension_types
        self._dimensions = dimensions
        self._slug_dimension_type_name = slug_dimension_type_name

    async def create_configuration(
        self,
        *,
        body: dict | list,
        dimension_ids: list[str],
        substitutions: list[dict] | None = None,
    ) -> dict:
        effective_substitutions = substitutions or []
        sentinel_paths = set(self.find_sentinel_paths(body))
        substitution_paths = {s["jsonpath"] for s in effective_substitutions}

        missing = sentinel_paths - substitution_paths
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValidationError(
                f"Sentinel paths missing substitutions: {missing_list}"
            )

        extra = substitution_paths - sentinel_paths
        if extra:
            extra_list = ", ".join(sorted(extra))
            raise ValidationError(
                f"Substitution paths have no sentinel in body: {extra_list}"
            )

        return await self._configurations.create_configuration(
            body=body,
            dimension_ids=dimension_ids,
            substitutions=substitutions,
        )

    @staticmethod
    def find_sentinel_paths(body: dict | list) -> list[str]:
        """Recursively traverse a JSON document and return all JSONPaths where
        the value equals exactly the string "_".

        JSONPath format:
        - Dict keys: $.field, $.nested.field
        - Array elements: $.array[0], $.array[0].nested
        - Mixed: $.servers[0].password
        """
        paths: list[str] = []

        def _traverse(node: object, prefix: str) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    child_prefix = f"{prefix}.{key}"
                    if value == "_":
                        paths.append(child_prefix)
                    else:
                        _traverse(value, child_prefix)
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    child_prefix = f"{prefix}[{index}]"
                    if value == "_":
                        paths.append(child_prefix)
                    else:
                        _traverse(value, child_prefix)

        _traverse(body, "$")
        return paths

    @staticmethod
    def apply_substitutions(body: dict | list, resolved: dict[str, Any]) -> dict | list:
        """Return a deep copy of body with JSONPath sentinel values replaced.

        resolved is a mapping of {jsonpath: value} where jsonpath is in the
        format produced by find_sentinel_paths (e.g. $.field, $.nested.field,
        $.array[0], $.array[0].nested).  Paths not present in resolved are left
        unchanged.
        """
        result = copy.deepcopy(body)
        for jsonpath, value in resolved.items():
            _set_path(result, jsonpath, value)
        return result

    async def apply_projection(
        self,
        *,
        body: dict | list,
        substitutions: list[dict],
        dimension_ids: list[str],
    ) -> dict | list:
        """Return body with all substitution sentinels replaced by resolved values.

        For each substitution, the current shared value revision for the given
        scope (dimension_ids) is resolved. If no revision is current for that
        scope, the sentinel "_" is left in place.
        """
        if not substitutions:
            return self.apply_substitutions(body, {})

        revisions = await asyncio.gather(
            *[
                self._shared_values.resolve_for_scope(
                    shared_value_id=str(sub["shared_value_id"]),
                    dimension_ids=dimension_ids,
                )
                for sub in substitutions
            ]
        )
        resolved: dict[str, Any] = {
            sub["jsonpath"]: (revision["value"] if revision else "_")
            for sub, revision in zip(substitutions, revisions, strict=True)
        }
        return self.apply_substitutions(body, resolved)

    async def resolve_from_names(
        self,
        *,
        slug_name: str,
        extra_dimensions: dict[str, str],
    ) -> dict:
        """Resolve configuration from a slug name and optional extra dimension names.

        Raises RuntimeError if dimension_types or dimensions were not injected.
        Raises NotFoundError for unknown slug or extra dimension values.
        Raises ValueError (via resolve_scope) if no configurations found for scope.
        """
        if self._dimension_types is None or self._dimensions is None:
            raise RuntimeError(
                "resolve_from_names requires dimension_types and dimensions "
                "to be injected"
            )

        # Load and sort dimension types by priority ascending
        dim_types = await self._dimension_types.get_dimension_types(
            include_archived=False
        )
        dim_types_sorted = sorted(dim_types, key=lambda dt: dt["priority"])

        if not dim_types_sorted:
            raise NotFoundError("No dimension types configured")

        # Resolve slug type from injected name; fall back to highest-priority
        slug_type = None
        if self._slug_dimension_type_name:
            target = self._slug_dimension_type_name
            slug_type = next(
                (dt for dt in dim_types_sorted if dt["name"] == target),
                None,
            )
            if slug_type is None:
                logger.warning(
                    "Configured slug_dimension_type_name=%r not found among "
                    "active dimension types; falling back to highest-priority type.",
                    self._slug_dimension_type_name,
                )
        if slug_type is None:
            slug_type = dim_types_sorted[0]

        # Resolve slug dimension
        slug_dim = await self._dimensions.get_by_type_and_name(
            type_id=str(slug_type["id"]), name=slug_name
        )
        if slug_dim is None:
            raise NotFoundError(f"Dimension '{slug_name}' not found")

        dimension_ids = [str(slug_dim["id"])]

        # Build name->type mapping for non-slug types
        name_to_type = {
            dt["name"]: dt
            for dt in dim_types_sorted
            if dt["id"] != slug_type["id"]
        }

        # Resolve extra dimensions matching known dimension type names
        for key, value in extra_dimensions.items():
            if key not in name_to_type:
                # Silently ignore unrecognised keys
                continue
            dt = name_to_type[key]
            dim = await self._dimensions.get_by_type_and_name(
                type_id=str(dt["id"]), name=value
            )
            if dim is None:
                raise NotFoundError(f"Dimension '{value}' not found for type '{key}'")
            dimension_ids.append(str(dim["id"]))

        # Fetch configs for the resolved scope
        configs = await self._configurations.get_for_rest_scope(
            dimension_ids=dimension_ids
        )

        return await self.resolve_scope(configs=configs, dimension_ids=dimension_ids)

    async def resolve_scope(
        self,
        *,
        configs: list[dict],
        dimension_ids: list[str],
    ) -> dict:
        """Merge projected configurations from least-specific to most-specific.

        Each config in configs (ordered least specific first) is projected via
        apply_projection with its substitutions. The resulting dicts are
        shallow-merged so that later (more specific) configs overwrite earlier
        top-level keys.

        Raises ValueError if configs is empty — callers should convert this to
        a 404 response.
        """
        if not configs:
            raise ValueError("No configurations found for scope")

        projections = []
        for config in configs:
            projected = await self.apply_projection(
                body=config["body"],
                substitutions=config["substitutions"],
                dimension_ids=dimension_ids,
            )
            projections.append(projected)

        result = {}
        for projected in projections:
            result.update(projected)
        return result
