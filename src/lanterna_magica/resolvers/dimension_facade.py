from ariadne import MutationType, QueryType

from lanterna_magica.data.dimension_types import DimensionTypes
from lanterna_magica.data.dimensions import Dimensions
from lanterna_magica.errors import NotFoundError


class DimensionFacadeResolver:
    def __init__(self, dimensions: Dimensions, dimension_types: DimensionTypes, type_name: str):
        self.dimensions = dimensions
        self.dimension_types = dimension_types
        self.type_name = type_name
        self._type_id: str | None = None

    async def _get_type_id(self) -> str:
        if self._type_id is None:
            types = await self.dimension_types.get_dimension_types()
            for t in types:
                if t["name"] == self.type_name:
                    self._type_id = str(t["id"])
                    break
            if self._type_id is None:
                raise NotFoundError(f"Dimension type '{self.type_name}' not found")
        return self._type_id

    async def resolve_list(
        self, _obj, info, *, search=None, include_archived=False, first=None, after=None
    ):
        type_id = await self._get_type_id()
        return await self.dimensions.get_dimensions(
            type_id=type_id,
            search=search,
            include_base=False,
            include_archived=include_archived,
            first=first,
            after=after,
        )

    async def resolve_by_id(self, _obj, info, *, id):
        return await info.context["dimension_loader"].load(id)

    async def resolve_create(self, _obj, info, *, input):
        type_id = await self._get_type_id()
        return await self.dimensions.create_dimension(
            type_id=type_id,
            name=input["name"],
            description=input.get("description"),
        )

    async def resolve_update(self, _obj, info, *, input):
        return await self.dimensions.update_dimension(
            id=input["id"],
            name=input.get("name"),
            description=input.get("description"),
        )

    async def resolve_archive(self, _obj, info, *, id):
        return await self.dimensions.archive_dimension(id)

    async def resolve_unarchive(self, _obj, info, *, id):
        return await self.dimensions.unarchive_dimension(id)


def get_facade_resolvers(
    dimensions: Dimensions,
    dimension_types: DimensionTypes,
    name: str,
) -> list:
    resolver = DimensionFacadeResolver(dimensions, dimension_types, name)
    plural = f"{name}s"

    query = QueryType()
    mutation = MutationType()

    query.set_field(plural, resolver.resolve_list)
    query.set_field(name, resolver.resolve_by_id)
    mutation.set_field(f"create{name.title()}", resolver.resolve_create)
    mutation.set_field(f"update{name.title()}", resolver.resolve_update)
    mutation.set_field(f"archive{name.title()}", resolver.resolve_archive)
    mutation.set_field(f"unarchive{name.title()}", resolver.resolve_unarchive)

    return [query, mutation]
