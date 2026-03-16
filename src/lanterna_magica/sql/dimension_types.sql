-- name: get_dimension_types(include_archived)
select id, name, priority, created_at, archived_at
from dimension_types
where (:include_archived::boolean OR archived_at IS NULL)
order by priority;

-- name: get_dimension_types_by_ids(ids)
select id, name, priority, created_at, archived_at
from dimension_types
where id = any(:ids::uuid[])
order by id;

-- name: create_dimension_type(name)^
insert into dimension_types (name, priority)
values (:name, coalesce((select max(priority) from dimension_types), 0) + 1)
returning id, name, priority, created_at, archived_at;

-- name: update_dimension_type(id, name)^
update dimension_types
set name = :name
where id = :id::uuid
  and archived_at is null
returning id, name, priority, created_at, archived_at;

-- name: get_dimension_type_priority(id)^
select priority from dimension_types where id = :id::uuid;

-- name: set_dimension_type_priority(id, priority)!
update dimension_types set priority = :priority where id = :id::uuid;

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
