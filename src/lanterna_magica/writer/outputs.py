from __future__ import annotations

import itertools
import logging
import os
from collections import defaultdict

from lanterna_magica.data.configurations import Configurations
from lanterna_magica.data.dimension_types import DimensionTypes
from lanterna_magica.data.outputs import Outputs
from lanterna_magica.data.utils import compute_scope_hash
from lanterna_magica.errors import NotFoundError
from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator

logger = logging.getLogger(__name__)


class OutputWriter:
    def __init__(
        self,
        outputs: Outputs,
        configurations: Configurations,
        orchestrator: ConfigurationOrchestrator,
        dimension_types: DimensionTypes,
    ):
        self._outputs = outputs
        self._configurations = configurations
        self._orchestrator = orchestrator
        self._dimension_types = dimension_types

    async def write(
        self,
        *,
        output_id: str,
    ) -> list[dict]:
        """Compute all dimension combinations for an output, resolve and write files.

        Args:
            output_id: The UUID of the output to write.

        Returns:
            List of result dicts — one per combination, from upsert_result.

        Raises:
            NotFoundError: If the output is not found or is archived.
        """
        # Step 1: Load the output definition.
        output = await self._outputs.get(id=output_id)
        if output is None or output.get("archived_at") is not None:
            raise NotFoundError("Output not found or archived")

        # Step 2: Load the dimensions for this output.
        dimensions = await self._outputs.get_dimensions(output_id=output_id)

        # Build type_id -> type_name mapping by fetching dimension type names.
        unique_type_ids = list(dict.fromkeys(str(dim["type_id"]) for dim in dimensions))
        fetched_types = (
            await self._dimension_types.get_dimension_types_by_ids(unique_type_ids)
            if unique_type_ids
            else []
        )
        type_id_to_name: dict[str, str] = {
            str(dt["id"]): dt["name"] for dt in fetched_types
        }

        # Step 3: Group dimensions by type_id and compute cartesian product.
        groups: dict[str, list[dict]] = defaultdict(list)
        for dim in dimensions:
            groups[str(dim["type_id"])].append(dim)

        if not groups:
            # No dimensions means a single empty combination (global scope).
            combinations: list[dict[str, dict]] = [{}]
        else:
            type_ids = list(groups.keys())
            dimension_lists = [groups[tid] for tid in type_ids]
            combinations = [
                {type_ids[i]: dim for i, dim in enumerate(combo)}
                for combo in itertools.product(*dimension_lists)
            ]

        results: list[dict] = []

        for combination in combinations:
            # Step 5a: Extract dimension_ids for this combination.
            dimension_ids = [str(dim["id"]) for dim in combination.values()]

            # Step 5b: Compute scope_hash.
            scope_hash = (
                compute_scope_hash(dimension_ids)
                if dimension_ids
                else compute_scope_hash([])
            )

            # Step 5c: Fetch configs for this scope.
            configs = await self._configurations.get_for_rest_scope(
                dimension_ids=dimension_ids
            )

            # Step 5d: Resolve scope.
            try:
                resolved = await self._orchestrator.resolve_scope(
                    configs=configs, dimension_ids=dimension_ids
                )
            except ValueError:
                # No configs for this scope — record failure and continue.
                path = _render_path(
                    output["path_template"], combination, type_id_to_name
                )
                result = await self._outputs.upsert_result(
                    output_id=output_id,
                    scope_hash=scope_hash,
                    path=path,
                    content="",
                    succeeded=False,
                    error="No configurations found for scope",
                )
                results.append(result)
                continue

            # Step 5e: Render path template.
            path = _render_path(output["path_template"], combination, type_id_to_name)

            # Step 5f: Serialize.
            content, _media_type = self._orchestrator.serialize(
                resolved, output["format"]
            )

            # Step 5g: Write to disk.
            try:
                parent_dir = os.path.dirname(path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with open(path, "w") as fh:
                    fh.write(content)
            except OSError as exc:
                result = await self._outputs.upsert_result(
                    output_id=output_id,
                    scope_hash=scope_hash,
                    path=path,
                    content=content,
                    succeeded=False,
                    error=str(exc),
                )
                results.append(result)
                continue

            # Step 5h: Upsert result.
            result = await self._outputs.upsert_result(
                output_id=output_id,
                scope_hash=scope_hash,
                path=path,
                content=content,
                succeeded=True,
                error=None,
            )
            results.append(result)

        return results


def _render_path(
    path_template: str,
    combination: dict[str, dict],
    type_id_to_name: dict[str, str],
) -> str:
    """Replace {type_name} placeholders in path_template with dimension names.

    For each type_id in the combination, looks up the type_name (using
    type_id_to_name); falls back to the type_id string if not found.
    Then replaces ``{<type_name>}`` in the template with the dimension's name.
    """
    path = path_template
    for type_id, dim in combination.items():
        placeholder_key = type_id_to_name.get(type_id, type_id)
        placeholder = "{" + placeholder_key + "}"
        path = path.replace(placeholder, dim["name"])
    return path
