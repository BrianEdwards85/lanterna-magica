-- name: get_dimension_types(include_archived)
select id, name, priority, created_at, archived_at
from dimension_types
where (:include_archived::boolean OR archived_at IS NULL)
order by priority;

-- name: get_dimension_types_by_ids(ids)
select id, name, priority, created_at, archived_at
from dimension_types
where id = any(:ids::uuid[]);

-- name: create_dimension_type(name, priority)^
insert into dimension_types (name, priority)
values (:name, :priority)
returning id, name, priority, created_at, archived_at;

-- name: archive_dimension_type(id)^
update dimension_types
set archived_at = now()
where id = :id
  and archived_at is null
returning id, name, priority, created_at, archived_at;

-- name: unarchive_dimension_type(id)^
update dimension_types
set archived_at = null
where id = :id
  and archived_at is not null
returning id, name, priority, created_at, archived_at;
