from ariadne import MutationType, ObjectType, QueryType

from lanterna_magica.data.outputs import Outputs
from lanterna_magica.writer.outputs import OutputWriter


class OutputsResolver:
    def __init__(self, outputs: Outputs, writer: OutputWriter):
        self.outputs = outputs
        self.writer = writer

    async def resolve_outputs(
        self, _obj, info, *, include_archived=False, first=None, after=None
    ):
        return await self.outputs.list(
            include_archived=include_archived,
            first=first,
            after=after,
        )

    async def resolve_output(self, _obj, info, *, id):
        return await self.outputs.get(id=id)

    async def resolve_create_output(self, _obj, info, *, input):
        return await self.outputs.create(
            path_template=input["path_template"],
            format=input["format"],
            dimension_ids=input["dimension_ids"],
        )

    async def resolve_archive_output(self, _obj, info, *, id):
        return await self.outputs.archive(id=id)

    async def resolve_trigger_output(self, _obj, info, *, id):
        await self.writer.write(output_id=id)
        return await self.outputs.get(id=id)

    async def resolve_output_dimensions(self, obj, info):
        return await self.outputs.get_dimensions(output_id=str(obj["id"]))

    async def resolve_output_results(self, obj, info):
        return await self.outputs.get_results(output_id=str(obj["id"]))

    async def resolve_result_output(self, obj, info):
        return await self.outputs.get(id=str(obj["output_id"]))


def get_output_resolvers(outputs: Outputs, writer: OutputWriter) -> list:
    resolver = OutputsResolver(outputs, writer)

    query = QueryType()
    mutation = MutationType()
    output_type = ObjectType("Output")
    output_result_type = ObjectType("OutputResult")

    query.set_field("outputs", resolver.resolve_outputs)
    query.set_field("output", resolver.resolve_output)
    mutation.set_field("createOutput", resolver.resolve_create_output)
    mutation.set_field("archiveOutput", resolver.resolve_archive_output)
    mutation.set_field("triggerOutput", resolver.resolve_trigger_output)
    output_type.set_field("dimensions", resolver.resolve_output_dimensions)
    output_type.set_field("results", resolver.resolve_output_results)
    output_result_type.set_field("output", resolver.resolve_result_output)

    return [query, mutation, output_type, output_result_type]
