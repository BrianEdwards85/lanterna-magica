from ariadne import MutationType, ObjectType, QueryType

from lanterna_magica.data.dimension_types import DimensionTypes
from lanterna_magica.data.dimensions import Dimensions
from lanterna_magica.data.utils import build_connection


class DimensionTypesResolver:
    def __init__(self, dimension_types: DimensionTypes, dimensions: Dimensions):
        self.dimension_types = dimension_types
        self.dimensions = dimensions

    async def resolve_dimension_types(self, _obj, info, *, include_archived=False):
        return await self.dimension_types.get_dimension_types(
            include_archived=include_archived,
        )

    async def resolve_create_dimension_type(self, _obj, info, *, input):
        return await self.dimension_types.create_dimension_type(name=input["name"])

    async def resolve_update_dimension_type(self, _obj, info, *, input):
        return await self.dimension_types.update_dimension_type(id=input["id"], name=input["name"])

    async def resolve_swap_dimension_type_priorities(self, _obj, info, *, id_a, id_b):
        return await self.dimension_types.swap_dimension_type_priorities(id_a=id_a, id_b=id_b)

    async def resolve_archive_dimension_type(self, _obj, info, *, id):
        return await self.dimension_types.archive_dimension_type(id)

    async def resolve_unarchive_dimension_type(self, _obj, info, *, id):
        return await self.dimension_types.unarchive_dimension_type(id)

    async def resolve_dimensions_for_type(
        self,
        obj,
        info,
        *,
        include_base=True,
        include_archived=False,
        first=None,
        after=None,
        search=None,
    ):
        # Use DataLoader for the default case (no filtering, no pagination, no search)
        # to avoid N+1 queries when listing dimension types with their dimensions.
        if include_base and not include_archived and first is None and after is None and search is None:
            rows = await info.context["dimensions_by_type_loader"].load(str(obj["id"]))
            return build_connection(rows, "id", len(rows))
        return await self.dimensions.get_dimensions(
            type_id=str(obj["id"]),
            search=search,
            include_base=include_base,
            include_archived=include_archived,
            first=first,
            after=after,
        )


def get_dimension_type_resolvers(dimension_types: DimensionTypes, dimensions: Dimensions) -> list:
    resolver = DimensionTypesResolver(dimension_types, dimensions)

    query = QueryType()
    mutation = MutationType()
    dimension_type_type = ObjectType("DimensionType")

    query.set_field("dimensionTypes", resolver.resolve_dimension_types)
    mutation.set_field("createDimensionType", resolver.resolve_create_dimension_type)
    mutation.set_field("updateDimensionType", resolver.resolve_update_dimension_type)
    mutation.set_field("swapDimensionTypePriorities", resolver.resolve_swap_dimension_type_priorities)
    mutation.set_field("archiveDimensionType", resolver.resolve_archive_dimension_type)
    mutation.set_field("unarchiveDimensionType", resolver.resolve_unarchive_dimension_type)
    dimension_type_type.set_field("dimensions", resolver.resolve_dimensions_for_type)

    return [query, mutation, dimension_type_type]
