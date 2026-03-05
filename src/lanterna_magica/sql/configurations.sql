-- name: get_configurations(service_id, environment_id, include_global, after_id, page_limit)
select id, service_id, environment_id, body, is_current, created_at
from configurations
where (:service_id::uuid IS NULL OR service_id = :service_id OR (:include_global::boolean AND service_id = '00000000-0000-0000-0000-000000000000'))
  and (:environment_id::uuid IS NULL OR environment_id = :environment_id OR (:include_global::boolean AND environment_id = '00000000-0000-0000-0000-000000000000'))
  and (:after_id::uuid IS NULL OR id < :after_id)
order by id desc
limit :page_limit;

-- name: get_configurations_by_ids(ids)
select id, service_id, environment_id, body, is_current, created_at
from configurations
where id = any(:ids::uuid[]);

-- name: unset_current_configuration(service_id, environment_id)!
update configurations
set is_current = false
where service_id = :service_id
  and environment_id = :environment_id
  and is_current = true;

-- name: create_configuration(service_id, environment_id, body)^
insert into configurations (service_id, environment_id, body, is_current)
values (:service_id, :environment_id, :body::jsonb, true)
returning id, service_id, environment_id, body, is_current, created_at;

-- name: get_substitutions_for_config(configuration_id)
select id, configuration_id, jsonpath, shared_value_id, created_at
from config_substitutions
where configuration_id = :configuration_id
order by jsonpath;

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
