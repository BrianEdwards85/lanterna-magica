class Configurations:
    def __init__(self, pool):
        self.pool = pool

    async def get_configurations(self, *, service_id=None, environment_id=None, first=None, after=None):
        raise NotImplementedError

    async def create_configuration(self, *, service_id, environment_id, body, substitutions=None):
        raise NotImplementedError

    async def update_config_substitution(self, *, configuration_id, shared_value_id):
        raise NotImplementedError

    async def get_substitutions(self, *, configuration_id):
        raise NotImplementedError
