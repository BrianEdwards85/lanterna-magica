from ariadne import MutationType, ObjectType, QueryType

from lanterna_magica.data.configurations import Configurations
from lanterna_magica.orchestrator import ConfigurationOrchestrator


class ConfigurationsResolver:
    def __init__(
        self,
        configurations: Configurations,
        orchestrator: ConfigurationOrchestrator,
    ):
        self.configurations = configurations
        self.orchestrator = orchestrator

    async def resolve_configurations(
        self, _obj, info, *,
        dimension_ids=None, include_base=None, current_only=None,
        first=None, after=None,
    ):
        return await self.configurations.get_configurations(
            dimension_ids=dimension_ids,
            include_base=include_base if include_base is not None else True,
            current_only=current_only or False,
            first=first,
            after=after,
        )

    async def resolve_configuration(self, _obj, info, *, id):
        return await info.context["configuration_loader"].load(id)

    async def resolve_create_configuration(self, _obj, info, *, input):
        return await self.orchestrator.create_configuration(
            dimension_ids=input["dimension_ids"],
            body=input["body"],
            substitutions=input.get("substitutions"),
        )

    async def resolve_update_config_substitution(self, _obj, info, *, input):
        return await self.configurations.update_config_substitution(
            configuration_id=input["configuration_id"],
            jsonpath=input["jsonpath"],
            shared_value_id=input["shared_value_id"],
        )

    async def resolve_set_configuration_current(self, _obj, info, *, id, is_current):
        return await self.configurations.set_configuration_current(
            id=id, is_current=is_current,
        )

    async def resolve_config_dimensions(self, obj, info):
        return await info.context["config_scopes_loader"].load(str(obj["id"]))

    async def resolve_config_substitutions(self, obj, info):
        return await info.context["substitution_loader"].load(str(obj["id"]))

    async def resolve_substitution_configuration(self, obj, info):
        return await info.context["configuration_loader"].load(str(obj["configuration_id"]))

    async def resolve_substitution_shared_value(self, obj, info):
        return await info.context["shared_value_loader"].load(str(obj["shared_value_id"]))

    async def resolve_config_projection(self, obj, info):
        substitutions = await info.context["substitution_loader"].load(str(obj["id"]))
        scopes = await info.context["config_scopes_loader"].load(str(obj["id"]))
        dimension_ids = [str(s["id"]) for s in scopes]
        return await self.orchestrator.apply_projection(
            body=obj["body"],
            substitutions=substitutions,
            dimension_ids=dimension_ids,
        )

    async def resolve_extract_sentinel_paths(self, _obj, info, *, body):
        return self.orchestrator.find_sentinel_paths(body)


def get_configuration_resolvers(
    configurations: Configurations,
    orchestrator: ConfigurationOrchestrator,
) -> list:
    resolver = ConfigurationsResolver(configurations, orchestrator)

    query = QueryType()
    mutation = MutationType()
    configuration_type = ObjectType("Configuration")
    substitution_type = ObjectType("ConfigSubstitution")

    query.set_field("configurations", resolver.resolve_configurations)
    query.set_field("configuration", resolver.resolve_configuration)
    query.set_field("extractSentinelPaths", resolver.resolve_extract_sentinel_paths)
    mutation.set_field("createConfiguration", resolver.resolve_create_configuration)
    mutation.set_field("updateConfigSubstitution", resolver.resolve_update_config_substitution)
    mutation.set_field("setConfigurationCurrent", resolver.resolve_set_configuration_current)
    configuration_type.set_field("dimensions", resolver.resolve_config_dimensions)
    configuration_type.set_field("substitutions", resolver.resolve_config_substitutions)
    configuration_type.set_field("projection", resolver.resolve_config_projection)
    substitution_type.set_field("configuration", resolver.resolve_substitution_configuration)
    substitution_type.set_field("sharedValue", resolver.resolve_substitution_shared_value)

    return [query, mutation, configuration_type, substitution_type]
