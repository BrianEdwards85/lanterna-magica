from ariadne import MutationType, ObjectType, QueryType

from lanterna_magica.data.configurations import Configurations
from lanterna_magica.data.shared_values import SharedValues
from lanterna_magica.data.utils import build_connection


class SharedValuesResolver:
    def __init__(self, shared_values: SharedValues, configurations: Configurations):
        self.shared_values = shared_values
        self.configurations = configurations

    async def resolve_shared_values(
        self, _obj, info, *, include_archived=False, search=None, first=None, after=None
    ):
        return await self.shared_values.get_shared_values(
            include_archived=include_archived,
            search=search,
            first=first,
            after=after,
        )

    async def resolve_shared_values_by_ids(self, _obj, info, *, ids):
        rows = await self.shared_values.get_by_ids(ids=ids)
        loader = info.context["shared_value_loader"]
        for r in rows:
            loader.prime(str(r["id"]), r)
        return rows

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
            dimension_ids=input["dimension_ids"],
            value=input["value"],
        )

    async def resolve_resolve_shared_value(
        self, _obj, info, *, shared_value_id, dimension_ids
    ):
        return await self.shared_values.resolve_for_scope(
            shared_value_id=shared_value_id,
            dimension_ids=dimension_ids,
        )

    async def resolve_used_by(
        self, obj, info, *, include_archived=False, first=None, after=None
    ):
        # Use DataLoader for default case (no filtering, no pagination)
        if not include_archived and first is None and after is None:
            rows = await info.context["configs_by_shared_value_loader"].load(
                str(obj["id"])
            )
            return build_connection(rows, "id", len(rows))
        return await self.configurations.get_configurations_by_shared_value(
            shared_value_id=str(obj["id"]),
            include_archived=include_archived,
            first=first,
            after=after,
        )

    async def resolve_set_revision_current(self, _obj, info, *, id, is_current):
        return await self.shared_values.set_revision_current(
            id=id,
            is_current=is_current,
        )

    async def resolve_revisions(
        self,
        obj,
        info,
        *,
        dimension_ids=None,
        include_base=None,
        current_only=None,
        first=None,
        after=None,
    ):
        return await self.shared_values.get_revisions(
            shared_value_id=str(obj["id"]),
            dimension_ids=dimension_ids,
            include_base=include_base if include_base is not None else True,
            current_only=current_only or False,
            first=first,
            after=after,
        )

    async def resolve_revision_shared_value(self, obj, info):
        return await info.context["shared_value_loader"].load(
            str(obj["shared_value_id"])
        )

    async def resolve_revision_dimensions(self, obj, info):
        return await info.context["revision_scopes_loader"].load(str(obj["id"]))


def get_shared_value_resolvers(
    shared_values: SharedValues, configurations: Configurations
) -> list:
    resolver = SharedValuesResolver(shared_values, configurations)

    query = QueryType()
    mutation = MutationType()
    shared_value_type = ObjectType("SharedValue")
    revision_type = ObjectType("SharedValueRevision")

    query.set_field("sharedValues", resolver.resolve_shared_values)
    query.set_field("sharedValuesByIds", resolver.resolve_shared_values_by_ids)
    query.set_field("resolveSharedValue", resolver.resolve_resolve_shared_value)
    mutation.set_field("createSharedValue", resolver.resolve_create_shared_value)
    mutation.set_field("updateSharedValue", resolver.resolve_update_shared_value)
    mutation.set_field("archiveSharedValue", resolver.resolve_archive_shared_value)
    mutation.set_field("unarchiveSharedValue", resolver.resolve_unarchive_shared_value)
    mutation.set_field(
        "createSharedValueRevision", resolver.resolve_create_shared_value_revision
    )
    mutation.set_field("setRevisionCurrent", resolver.resolve_set_revision_current)
    shared_value_type.set_field("revisions", resolver.resolve_revisions)
    shared_value_type.set_field("usedBy", resolver.resolve_used_by)
    revision_type.set_field("sharedValue", resolver.resolve_revision_shared_value)
    revision_type.set_field("dimensions", resolver.resolve_revision_dimensions)

    return [query, mutation, shared_value_type, revision_type]
