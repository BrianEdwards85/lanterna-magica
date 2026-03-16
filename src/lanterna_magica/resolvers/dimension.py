from ariadne import MutationType, ObjectType, QueryType

from lanterna_magica.data.dimensions import Dimensions


class DimensionsResolver:
    def __init__(self, dimensions: Dimensions):
        self.dimensions = dimensions

    async def resolve_dimensions(
        self,
        _obj,
        info,
        *,
        type_id,
        search=None,
        include_base=True,
        include_archived=False,
        first=None,
        after=None,
    ):
        return await self.dimensions.get_dimensions(
            type_id=type_id,
            search=search,
            include_base=include_base,
            include_archived=include_archived,
            first=first,
            after=after,
        )

    async def resolve_dimensions_by_ids(self, _obj, info, *, ids):
        return await self.dimensions.get_by_ids(ids=ids)

    async def resolve_create_dimension(self, _obj, info, *, input):
        return await self.dimensions.create_dimension(
            type_id=input["type_id"],
            name=input["name"],
            description=input.get("description"),
        )

    async def resolve_update_dimension(self, _obj, info, *, input):
        return await self.dimensions.update_dimension(
            id=input["id"],
            name=input.get("name"),
            description=input.get("description"),
        )

    async def resolve_archive_dimension(self, _obj, info, *, id):
        return await self.dimensions.archive_dimension(id)

    async def resolve_unarchive_dimension(self, _obj, info, *, id):
        return await self.dimensions.unarchive_dimension(id)

    async def resolve_dimension_type(self, obj, info):
        return await info.context["dimension_type_loader"].load(str(obj["type_id"]))


def get_dimension_resolvers(dimensions: Dimensions) -> list:
    resolver = DimensionsResolver(dimensions)

    query = QueryType()
    mutation = MutationType()
    dimension_type = ObjectType("Dimension")

    query.set_field("dimensions", resolver.resolve_dimensions)
    query.set_field("dimensionsByIds", resolver.resolve_dimensions_by_ids)
    mutation.set_field("createDimension", resolver.resolve_create_dimension)
    mutation.set_field("updateDimension", resolver.resolve_update_dimension)
    mutation.set_field("archiveDimension", resolver.resolve_archive_dimension)
    mutation.set_field("unarchiveDimension", resolver.resolve_unarchive_dimension)
    dimension_type.set_field("type", resolver.resolve_dimension_type)

    return [query, mutation, dimension_type]
