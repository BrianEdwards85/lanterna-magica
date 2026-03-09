import asyncio
import copy
import re
from typing import Any

from lanterna_magica.errors import ValidationError

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
    def __init__(self, configurations, shared_values):
        self._configurations = configurations
        self._shared_values = shared_values

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
