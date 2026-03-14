-- name: get_configurations(dimension_ids, include_base, current_only, after_id, page_limit)
select distinct c.id, c.scope_hash, c.body, c.is_current, c.created_at
from configurations c
join configuration_scopes cs on cs.configuration_id = c.id
where (:dimension_ids::uuid[] IS NULL OR cs.dimension_id = any(:dimension_ids)
       OR (:include_base::boolean AND cs.dimension_id IN (
           select d.id from dimensions d where d.base = true
       )))
  and (:current_only::boolean IS FALSE OR c.is_current = true)
  and (:after_id::uuid IS NULL OR c.id < :after_id)
order by c.id desc
limit :page_limit;

-- name: get_configurations_by_ids(ids)
select id, scope_hash, body, is_current, created_at
from configurations
where id = any(:ids::uuid[]);

-- name: unset_current_configuration(scope_hash)!
update configurations
set is_current = false
where scope_hash = :scope_hash
  and is_current = true;

-- name: create_configuration(scope_hash, body)^
insert into configurations (scope_hash, body, is_current)
values (:scope_hash, :body::jsonb, true)
returning id, scope_hash, body, is_current, created_at;

-- name: insert_configuration_scope(configuration_id, dimension_id)!
insert into configuration_scopes (configuration_id, dimension_id)
values (:configuration_id, :dimension_id);

-- name: get_scopes_for_config(configuration_id)
select cs.dimension_id, d.id, d.type_id, d.name, d.description, d.base
from configuration_scopes cs
join dimensions d on d.id = cs.dimension_id
where cs.configuration_id = :configuration_id
order by d.type_id;

-- name: get_scopes_by_config_ids(ids)
select cs.configuration_id, d.id, d.type_id, d.name, d.description, d.base
from configuration_scopes cs
join dimensions d on d.id = cs.dimension_id
where cs.configuration_id = any(:ids::uuid[])
order by cs.configuration_id, d.type_id;

-- name: get_substitutions_for_config(configuration_id)
select id, configuration_id, jsonpath, shared_value_id, created_at
from config_substitutions
where configuration_id = :configuration_id
order by jsonpath;

-- name: get_substitutions_by_config_ids(ids)
select id, configuration_id, jsonpath, shared_value_id, created_at
from config_substitutions
where configuration_id = any(:ids::uuid[])
order by configuration_id, jsonpath;

-- name: create_config_substitution(configuration_id, jsonpath, shared_value_id)^
insert into config_substitutions (configuration_id, jsonpath, shared_value_id)
values (:configuration_id, :jsonpath, :shared_value_id)
returning id, configuration_id, jsonpath, shared_value_id, created_at;

-- name: update_config_substitution(configuration_id, jsonpath, shared_value_id)^
update config_substitutions
set shared_value_id = :shared_value_id
where configuration_id = :configuration_id
  and jsonpath = :jsonpath
returning id, configuration_id, jsonpath, shared_value_id, created_at;

-- name: set_configuration_current(id)^
update configurations
set is_current = true
where id = :id
  and is_current = false
returning id, scope_hash, body, is_current, created_at;

-- name: unset_single_configuration_current(id)^
update configurations
set is_current = false
where id = :id
  and is_current = true
returning id, scope_hash, body, is_current, created_at;

-- name: backfill_configuration_scopes(dimension_id)!
insert into configuration_scopes (configuration_id, dimension_id)
select c.id, :dimension_id::uuid
from configurations c
where not exists (
    select 1 from configuration_scopes cs
    where cs.configuration_id = c.id and cs.dimension_id = :dimension_id::uuid
);

-- name: recompute_configuration_scope_hashes()!
update configurations c
set scope_hash = sub.new_hash
from (
    select cs.configuration_id,
           md5(string_agg(cs.dimension_id::text, ',' order by cs.dimension_id::text))::uuid as new_hash
    from configuration_scopes cs
    group by cs.configuration_id
) sub
where c.id = sub.configuration_id
  and c.scope_hash is distinct from sub.new_hash;

-- name: get_configurations_by_shared_value_id(shared_value_id, include_archived, after_id, page_limit)
select c.id, c.scope_hash, c.body, c.is_current, c.created_at, c.created_by
from configurations c
join config_substitutions cs on cs.configuration_id = c.id
where cs.shared_value_id = :shared_value_id
  and (:include_archived::boolean or c.archived_at is null)
  and (:after_id::uuid is null or c.id < :after_id)
order by c.id desc
limit :page_limit;
