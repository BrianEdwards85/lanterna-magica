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

-- name: get_revisions(shared_value_id, dimension_ids, include_base, current_only, after_id, page_limit)
select distinct r.id, r.shared_value_id, r.scope_hash, r.value, r.is_current, r.created_at
from shared_value_revisions r
join revision_scopes rs on rs.revision_id = r.id
where r.shared_value_id = :shared_value_id
  and (:dimension_ids::uuid[] IS NULL OR rs.dimension_id = any(:dimension_ids)
       OR (:include_base::boolean AND rs.dimension_id IN (
           select d.id from dimensions d where d.base = true
       )))
  and (:current_only::boolean IS FALSE OR r.is_current = true)
  and (:after_id::uuid IS NULL OR r.id < :after_id)
order by r.id desc
limit :page_limit;

-- name: unset_current_revision(shared_value_id, scope_hash)!
update shared_value_revisions
set is_current = false
where shared_value_id = :shared_value_id
  and scope_hash = :scope_hash
  and is_current = true;

-- name: create_revision(shared_value_id, scope_hash, value)^
insert into shared_value_revisions (shared_value_id, scope_hash, value, is_current)
values (:shared_value_id, :scope_hash, :value::jsonb, true)
returning id, shared_value_id, scope_hash, value, is_current, created_at;

-- name: insert_revision_scope(revision_id, dimension_id)!
insert into revision_scopes (revision_id, dimension_id)
values (:revision_id, :dimension_id);

-- name: get_scopes_for_revision(revision_id)
select rs.revision_id, d.id, d.type_id, d.name, d.description, d.base
from revision_scopes rs
join dimensions d on d.id = rs.dimension_id
where rs.revision_id = :revision_id
order by d.type_id;

-- name: get_scopes_by_revision_ids(ids)
select rs.revision_id, d.id, d.type_id, d.name, d.description, d.base
from revision_scopes rs
join dimensions d on d.id = rs.dimension_id
where rs.revision_id = any(:ids::uuid[])
order by rs.revision_id, d.type_id;

-- name: backfill_revision_scopes(dimension_id)!
insert into revision_scopes (revision_id, dimension_id)
select r.id, :dimension_id::uuid
from shared_value_revisions r
where not exists (
    select 1 from revision_scopes rs
    where rs.revision_id = r.id and rs.dimension_id = :dimension_id::uuid
);

-- name: recompute_revision_scope_hashes()!
update shared_value_revisions r
set scope_hash = sub.new_hash
from (
    select rs.revision_id,
           md5(string_agg(rs.dimension_id::text, ',' order by rs.dimension_id::text))::uuid as new_hash
    from revision_scopes rs
    group by rs.revision_id
) sub
where r.id = sub.revision_id
  and r.scope_hash is distinct from sub.new_hash;
