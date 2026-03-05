from ariadne import MutationType, ObjectType, QueryType


class ConfigurationsResolver:
    def __init__(self, configurations):
        self.configurations = configurations

    # -- Query resolvers --

    async def resolve_configurations(
        self, _obj, info, *, service_id=None, environment_id=None, first=None, after=None
    ):
        return await self.configurations.get_configurations(
            service_id=service_id,
            environment_id=environment_id,
            first=first,
            after=after,
        )

    async def resolve_configuration(self, _obj, info, *, id):
        return await info.context["configuration_loader"].load(id)

    # -- Mutation resolvers --

    async def resolve_create_configuration(self, _obj, info, *, input):
        return await self.configurations.create_configuration(
            service_id=input["service_id"],
            environment_id=input["environment_id"],
            body=input["body"],
            substitutions=input.get("substitutions"),
        )

    async def resolve_update_config_substitution(self, _obj, info, *, input):
        return await self.configurations.update_config_substitution(
            configuration_id=input["configuration_id"],
            jsonpath=input["jsonpath"],
            shared_value_id=input["shared_value_id"],
        )

    # -- Configuration field resolvers --

    async def resolve_config_service(self, obj, info):
        return await info.context["service_loader"].load(str(obj["service_id"]))

    async def resolve_config_environment(self, obj, info):
        return await info.context["environment_loader"].load(str(obj["environment_id"]))

    async def resolve_config_substitutions(self, obj, info):
        return await self.configurations.get_substitutions(
            configuration_id=str(obj["id"])
        )

    # -- ConfigSubstitution field resolvers --

    async def resolve_substitution_configuration(self, obj, info):
        return await info.context["configuration_loader"].load(str(obj["configuration_id"]))

    async def resolve_substitution_shared_value(self, obj, info):
        return await info.context["shared_value_loader"].load(str(obj["shared_value_id"]))


def get_configuration_resolvers(configurations) -> list:
    resolver = ConfigurationsResolver(configurations)

    query = QueryType()
    mutation = MutationType()
    configuration_type = ObjectType("Configuration")
    substitution_type = ObjectType("ConfigSubstitution")

    query.set_field("configurations", resolver.resolve_configurations)
    query.set_field("configuration", resolver.resolve_configuration)
    mutation.set_field("createConfiguration", resolver.resolve_create_configuration)
    mutation.set_field("updateConfigSubstitution", resolver.resolve_update_config_substitution)
    configuration_type.set_field("service", resolver.resolve_config_service)
    configuration_type.set_field("environment", resolver.resolve_config_environment)
    configuration_type.set_field("substitutions", resolver.resolve_config_substitutions)
    substitution_type.set_field("configuration", resolver.resolve_substitution_configuration)
    substitution_type.set_field("sharedValue", resolver.resolve_substitution_shared_value)

    return [query, mutation, configuration_type, substitution_type]
