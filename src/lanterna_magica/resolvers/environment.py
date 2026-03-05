from ariadne import MutationType, QueryType

from lanterna_magica.data.environments import Environments


class EnvironmentsResolver:
    def __init__(self, environments: Environments):
        self.environments = environments

    async def resolve_environments(
        self, _obj, info, *, search=None, include_archived=False, first=None, after=None
    ):
        return await self.environments.get_environments(
            search=search,
            include_archived=include_archived,
            first=first,
            after=after,
        )

    async def resolve_environment(self, _obj, info, *, id):
        return await info.context["environment_loader"].load(id)

    async def resolve_create_environment(self, _obj, info, *, input):
        return await self.environments.create_environment(
            name=input["name"], description=input.get("description")
        )

    async def resolve_update_environment(self, _obj, info, *, input):
        return await self.environments.update_environment(
            id=input["id"], name=input.get("name"), description=input.get("description")
        )

    async def resolve_archive_environment(self, _obj, info, *, id):
        return await self.environments.archive_environment(id)

    async def resolve_unarchive_environment(self, _obj, info, *, id):
        return await self.environments.unarchive_environment(id)


def get_environment_resolvers(environments: Environments) -> list:
    resolver = EnvironmentsResolver(environments)

    query = QueryType()
    mutation = MutationType()

    query.set_field("environments", resolver.resolve_environments)
    query.set_field("environment", resolver.resolve_environment)
    mutation.set_field("createEnvironment", resolver.resolve_create_environment)
    mutation.set_field("updateEnvironment", resolver.resolve_update_environment)
    mutation.set_field("archiveEnvironment", resolver.resolve_archive_environment)
    mutation.set_field("unarchiveEnvironment", resolver.resolve_unarchive_environment)

    return [query, mutation]
