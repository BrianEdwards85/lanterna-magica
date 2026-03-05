from ariadne import MutationType, QueryType

from lanterna_magica.data.services import Services


class ServicesResolver:
    def __init__(self, services: Services):
        self.services = services

    async def resolve_services(
        self, _obj, info, *, search=None, include_archived=False, first=None, after=None
    ):
        return await self.services.get_services(
            search=search,
            include_archived=include_archived,
            first=first,
            after=after,
        )

    async def resolve_service(self, _obj, info, *, id):
        return await info.context["service_loader"].load(id)

    async def resolve_create_service(self, _obj, info, *, input):
        return await self.services.create_service(
            name=input["name"], description=input.get("description")
        )

    async def resolve_update_service(self, _obj, info, *, input):
        return await self.services.update_service(
            id=input["id"], name=input.get("name"), description=input.get("description")
        )

    async def resolve_archive_service(self, _obj, info, *, id):
        return await self.services.archive_service(id)

    async def resolve_unarchive_service(self, _obj, info, *, id):
        return await self.services.unarchive_service(id)


def get_service_resolvers(services: Services) -> list:
    resolver = ServicesResolver(services)

    query = QueryType()
    mutation = MutationType()

    query.set_field("services", resolver.resolve_services)
    query.set_field("service", resolver.resolve_service)
    mutation.set_field("createService", resolver.resolve_create_service)
    mutation.set_field("updateService", resolver.resolve_update_service)
    mutation.set_field("archiveService", resolver.resolve_archive_service)
    mutation.set_field("unarchiveService", resolver.resolve_unarchive_service)

    return [query, mutation]
