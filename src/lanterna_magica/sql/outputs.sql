-- name: create_output(path_template, format)^
insert into outputs (path_template, format)
values (:path_template, :format)
returning id, path_template, format, created_at, updated_at, archived_at;

-- name: get_output(id)^
select id, path_template, format, created_at, updated_at, archived_at
from outputs
where id = :id;

-- name: get_outputs(include_archived, after_id, page_limit)
select id, path_template, format, created_at, updated_at, archived_at
from outputs
where (:include_archived::boolean OR archived_at IS NULL)
  and (:after_id::uuid IS NULL OR id < :after_id)
order by id desc
limit :page_limit;

-- name: archive_output(id)^
update outputs
set archived_at = now(),
    updated_at = now()
where id = :id
  and archived_at is null
returning id, path_template, format, created_at, updated_at, archived_at;

-- name: insert_output_dimension(output_id, dimension_id)!
insert into output_dimensions (output_id, dimension_id)
values (:output_id, :dimension_id);

-- name: get_dimensions_for_output(output_id)
select d.id, d.type_id, d.name, d.description, d.base, d.created_at, d.updated_at, d.archived_at
from dimensions d
join output_dimensions od on od.dimension_id = d.id
where od.output_id = :output_id;

-- name: upsert_output_result(output_id, scope_hash, path, content, succeeded, error, written_by)^
insert into output_results (output_id, scope_hash, path, content, succeeded, error, written_by)
values (:output_id, :scope_hash, :path, :content, :succeeded, :error, :written_by)
on conflict (output_id, scope_hash) do update
set path = excluded.path,
    content = excluded.content,
    succeeded = excluded.succeeded,
    error = excluded.error,
    written_at = now(),
    written_by = excluded.written_by
returning id, output_id, scope_hash, path, content, succeeded, error, written_at, written_by;

-- name: get_results_for_output(output_id)
select id, output_id, scope_hash, path, content, succeeded, error, written_at, written_by
from output_results
where output_id = :output_id
order by path asc;
