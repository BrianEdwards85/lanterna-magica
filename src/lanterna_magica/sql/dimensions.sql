-- name: get_dimensions(type_id, include_archived, search, after_id, page_limit)
select id, type_id, name, description, base, created_at, updated_at, archived_at
from dimensions
where type_id = :type_id
  and base = false
  and (:include_archived::boolean OR archived_at IS NULL)
  and (:search::text IS NULL OR name ILIKE '%' || :search || '%' ESCAPE '\' OR description ILIKE '%' || :search || '%' ESCAPE '\')
  and (:after_id::uuid IS NULL OR id < :after_id)
order by id desc
limit :page_limit;

-- name: get_dimensions_by_ids(ids)
select id, type_id, name, description, base, created_at, updated_at, archived_at
from dimensions
where id = any(:ids::uuid[]);

-- name: get_base_dimension(type_id)^
select id, type_id, name, description, base, created_at, updated_at, archived_at
from dimensions
where type_id = :type_id
  and base = true;

-- name: create_dimension(type_id, name, description)^
insert into dimensions (type_id, name, description)
values (:type_id, :name, :description)
returning id, type_id, name, description, base, created_at, updated_at, archived_at;

-- name: update_dimension(id, name, description)^
update dimensions
set name = coalesce(:name, name),
    description = coalesce(:description, description),
    updated_at = now()
where id = :id
  and base = false
  and archived_at is null
returning id, type_id, name, description, base, created_at, updated_at, archived_at;

-- name: archive_dimension(id)^
update dimensions
set archived_at = now(),
    updated_at = now()
where id = :id
  and base = false
  and archived_at is null
returning id, type_id, name, description, base, created_at, updated_at, archived_at;

-- name: unarchive_dimension(id)^
update dimensions
set archived_at = null,
    updated_at = now()
where id = :id
  and base = false
  and archived_at is not null
returning id, type_id, name, description, base, created_at, updated_at, archived_at;
