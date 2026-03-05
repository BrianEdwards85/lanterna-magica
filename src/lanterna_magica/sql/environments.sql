-- name: get_environments(include_archived, search, after_id, page_limit)
select id, name, description, created_at, updated_at, archived_at
from environments
where id != '00000000-0000-0000-0000-000000000000'
  and (:include_archived::boolean OR archived_at IS NULL)
  and (:search::text IS NULL OR name ILIKE '%' || :search || '%' OR description ILIKE '%' || :search || '%')
  and (:after_id::uuid IS NULL OR id < :after_id)
order by id desc
limit :page_limit;

-- name: get_environments_by_ids(ids)
select id, name, description, created_at, updated_at, archived_at
from environments
where id = any(:ids::uuid[]);

-- name: create_environment(name, description)^
insert into environments (name, description)
values (:name, :description)
returning id, name, description, created_at, updated_at, archived_at;

-- name: update_environment(id, name, description)^
update environments
set name = coalesce(:name, name),
    description = coalesce(:description, description),
    updated_at = now()
where id = :id
  and archived_at is null
returning id, name, description, created_at, updated_at, archived_at;

-- name: archive_environment(id)^
update environments
set archived_at = now(),
    updated_at = now()
where id = :id
  and archived_at is null
returning id, name, description, created_at, updated_at, archived_at;

-- name: unarchive_environment(id)^
update environments
set archived_at = null,
    updated_at = now()
where id = :id
  and archived_at is not null
returning id, name, description, created_at, updated_at, archived_at;
