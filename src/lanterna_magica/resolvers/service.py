from datetime import datetime, timezone

from ariadne import MutationType, QueryType

_STUB_SERVICE = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "stub-service",
    "description": "Stubbed placeholder",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "archived_at": None,
}

_STUB_CONNECTION = {
    "edges": [{"node": _STUB_SERVICE, "cursor": "stub-cursor"}],
    "page_info": {"has_next_page": False, "end_cursor": None},
}


class ServicesResolver:
    async def resolve_services(self, _obj, info, **kwargs):
        return _STUB_CONNECTION

    async def resolve_service(self, _obj, info, *, id):
        return _STUB_SERVICE

    async def resolve_create_service(self, _obj, info, *, input):
        return _STUB_SERVICE

    async def resolve_update_service(self, _obj, info, *, input):
        return _STUB_SERVICE

    async def resolve_archive_service(self, _obj, info, *, id):
        return _STUB_SERVICE

    async def resolve_unarchive_service(self, _obj, info, *, id):
        return _STUB_SERVICE


def get_service_resolvers() -> list:
    resolver = ServicesResolver()
    query = QueryType()
    mutation = MutationType()

    query.set_field("services", resolver.resolve_services)
    query.set_field("service", resolver.resolve_service)
    mutation.set_field("createService", resolver.resolve_create_service)
    mutation.set_field("updateService", resolver.resolve_update_service)
    mutation.set_field("archiveService", resolver.resolve_archive_service)
    mutation.set_field("unarchiveService", resolver.resolve_unarchive_service)

    return [query, mutation]
