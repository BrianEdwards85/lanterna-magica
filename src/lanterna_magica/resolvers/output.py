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

    async def resolve_outputs_by_ids(self, _obj, info, *, ids):
        rows = await self.outputs.get_by_ids(ids=ids)
        loader = info.context["output_loader"]
        for r in rows:
            loader.prime(str(r["id"]), r)
        return rows

    async def resolve_create_output(self, _obj, info, *, input):
        return await self.outputs.create(
            path_template=input["path_template"],
            format=input["format"],
            dimension_ids=input["dimension_ids"],
        )

    async def resolve_archive_output(self, _obj, info, *, id):
        return await self.outputs.archive(id=id)

    async def resolve_trigger_output(self, _obj, info, *, id):
        loader = info.context["output_loader"]
        await self.writer.write(
            output_id=id,
            on_complete=lambda: loader.clear(id),
        )
        return await loader.load(id)

    async def resolve_output_dimensions(self, obj, info):
        return await info.context["output_dimensions_loader"].load(str(obj["id"]))

    async def resolve_output_results(self, obj, info):
        return await info.context["output_results_loader"].load(str(obj["id"]))

    async def resolve_result_output(self, obj, info):
        return await info.context["output_loader"].load(str(obj["output_id"]))


def get_output_resolvers(outputs: Outputs, writer: OutputWriter) -> list:
    resolver = OutputsResolver(outputs, writer)

    query = QueryType()
    mutation = MutationType()
    output_type = ObjectType("Output")
    output_result_type = ObjectType("OutputResult")

    query.set_field("outputs", resolver.resolve_outputs)
    query.set_field("outputsByIds", resolver.resolve_outputs_by_ids)
    mutation.set_field("createOutput", resolver.resolve_create_output)
    mutation.set_field("archiveOutput", resolver.resolve_archive_output)
    mutation.set_field("triggerOutput", resolver.resolve_trigger_output)
    output_type.set_field("dimensions", resolver.resolve_output_dimensions)
    output_type.set_field("results", resolver.resolve_output_results)
    output_result_type.set_field("output", resolver.resolve_result_output)

    return [query, mutation, output_type, output_result_type]
