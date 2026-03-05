from ariadne import MutationType, ObjectType, QueryType

from lanterna_magica.data.shared_values import SharedValues


class SharedValuesResolver:
    def __init__(self, shared_values: SharedValues):
        self.shared_values = shared_values

    async def resolve_shared_values(
        self, _obj, info, *, search=None, include_archived=False, first=None, after=None
    ):
        return await self.shared_values.get_shared_values(
            search=search,
            include_archived=include_archived,
            first=first,
            after=after,
        )

    async def resolve_shared_value(self, _obj, info, *, id):
        return await info.context["shared_value_loader"].load(id)

    async def resolve_create_shared_value(self, _obj, info, *, input):
        return await self.shared_values.create_shared_value(name=input["name"])

    async def resolve_update_shared_value(self, _obj, info, *, input):
        return await self.shared_values.update_shared_value(
            id=input["id"], name=input.get("name")
        )

    async def resolve_archive_shared_value(self, _obj, info, *, id):
        return await self.shared_values.archive_shared_value(id)

    async def resolve_unarchive_shared_value(self, _obj, info, *, id):
        return await self.shared_values.unarchive_shared_value(id)

    async def resolve_create_shared_value_revision(self, _obj, info, *, input):
        return await self.shared_values.create_revision(
            shared_value_id=input["shared_value_id"],
            service_id=input["service_id"],
            environment_id=input["environment_id"],
            value=input["value"],
        )

    async def resolve_revisions(
        self, obj, info, *, service_id=None, environment_id=None, current_only=None, first=None, after=None
    ):
        return await self.shared_values.get_revisions(
            shared_value_id=str(obj["id"]),
            service_id=service_id,
            environment_id=environment_id,
            current_only=current_only or False,
            first=first,
            after=after,
        )

    # -- SharedValueRevision field resolvers --

    async def resolve_revision_shared_value(self, obj, info):
        return await info.context["shared_value_loader"].load(str(obj["shared_value_id"]))

    async def resolve_revision_service(self, obj, info):
        return await info.context["service_loader"].load(str(obj["service_id"]))

    async def resolve_revision_environment(self, obj, info):
        return await info.context["environment_loader"].load(str(obj["environment_id"]))


def get_shared_value_resolvers(shared_values: SharedValues) -> list:
    resolver = SharedValuesResolver(shared_values)

    query = QueryType()
    mutation = MutationType()
    shared_value_type = ObjectType("SharedValue")
    revision_type = ObjectType("SharedValueRevision")

    query.set_field("sharedValues", resolver.resolve_shared_values)
    query.set_field("sharedValue", resolver.resolve_shared_value)
    mutation.set_field("createSharedValue", resolver.resolve_create_shared_value)
    mutation.set_field("updateSharedValue", resolver.resolve_update_shared_value)
    mutation.set_field("archiveSharedValue", resolver.resolve_archive_shared_value)
    mutation.set_field("unarchiveSharedValue", resolver.resolve_unarchive_shared_value)
    mutation.set_field("createSharedValueRevision", resolver.resolve_create_shared_value_revision)
    shared_value_type.set_field("revisions", resolver.resolve_revisions)
    revision_type.set_field("sharedValue", resolver.resolve_revision_shared_value)
    revision_type.set_field("serviceId", resolver.resolve_revision_service)
    revision_type.set_field("environmentId", resolver.resolve_revision_environment)

    return [query, mutation, shared_value_type, revision_type]
