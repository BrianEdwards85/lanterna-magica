-- name: get_shared_values(include_archived, after_id, page_limit)
select id, name, created_at, updated_at, archived_at
from shared_values
where (:include_archived::boolean OR archived_at IS NULL)
  and (:after_id::uuid IS NULL OR id < :after_id)
order by id desc
limit :page_limit;

-- name: search_shared_values(query, include_archived, page_limit)
select id, name, created_at, updated_at, archived_at
from shared_values
where name % :query
  and (:include_archived::boolean OR archived_at IS NULL)
order by similarity(name, :query) desc, id
limit :page_limit;

-- name: get_shared_values_by_ids(ids)
select id, name, created_at, updated_at, archived_at
from shared_values
where id = any(:ids::uuid[]);

-- name: create_shared_value(name)^
insert into shared_values (name)
values (:name)
returning id, name, created_at, updated_at, archived_at;

-- name: update_shared_value(id, name)^
update shared_values
set name = coalesce(:name, name),
    updated_at = now()
where id = :id
  and archived_at is null
returning id, name, created_at, updated_at, archived_at;

-- name: archive_shared_value(id)^
update shared_values
set archived_at = now(),
    updated_at = now()
where id = :id
  and archived_at is null
returning id, name, created_at, updated_at, archived_at;

-- name: unarchive_shared_value(id)^
update shared_values
set archived_at = null,
    updated_at = now()
where id = :id
  and archived_at is not null
returning id, name, created_at, updated_at, archived_at;

-- name: get_revisions(shared_value_id, service_id, environment_id, include_global, current_only, after_id, page_limit)
select id, shared_value_id, service_id, environment_id, value, is_current, created_at
from shared_value_revisions
where shared_value_id = :shared_value_id
  and (:service_id::uuid IS NULL OR service_id = :service_id OR (:include_global::boolean AND service_id = '00000000-0000-0000-0000-000000000000'))
  and (:environment_id::uuid IS NULL OR environment_id = :environment_id OR (:include_global::boolean AND environment_id = '00000000-0000-0000-0000-000000000000'))
  and (:current_only::boolean IS FALSE OR is_current = true)
  and (:after_id::uuid IS NULL OR id < :after_id)
order by id desc
limit :page_limit;

-- name: unset_current_revision(shared_value_id, service_id, environment_id)!
update shared_value_revisions
set is_current = false
where shared_value_id = :shared_value_id
  and service_id = :service_id
  and environment_id = :environment_id
  and is_current = true;

-- name: create_revision(shared_value_id, service_id, environment_id, value)^
insert into shared_value_revisions (shared_value_id, service_id, environment_id, value, is_current)
values (:shared_value_id, :service_id, :environment_id, :value::jsonb, true)
returning id, shared_value_id, service_id, environment_id, value, is_current, created_at;
