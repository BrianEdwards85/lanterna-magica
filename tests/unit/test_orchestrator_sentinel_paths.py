from lanterna_magica.orchestrator.configuration import ConfigurationOrchestrator

# -- flat dict --


def test_flat_dict_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths({"password": "_"})
    assert result == ["$.password"]


def test_flat_dict_no_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"host": "localhost", "port": 5432})
    assert result == []


def test_flat_dict_mixed():
    result = ConfigurationOrchestrator.find_sentinel_paths({"host": "localhost", "password": "_"})
    assert result == ["$.password"]


# -- nested dict --


def test_nested_dict_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths({"db": {"host": "localhost", "password": "_"}})
    assert result == ["$.db.password"]


def test_nested_dict_multiple_sentinels():
    result = ConfigurationOrchestrator.find_sentinel_paths({"db": {"password": "_"}, "cache": {"secret": "_"}})
    assert set(result) == {"$.db.password", "$.cache.secret"}


def test_nested_dict_no_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"db": {"host": "localhost", "port": 5432}})
    assert result == []


# -- array of scalars --


def test_array_of_scalars_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths({"keys": ["_", "real"]})
    assert result == ["$.keys[0]"]


def test_array_of_scalars_no_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"keys": ["a", "b", "c"]})
    assert result == []


def test_array_of_scalars_multiple_sentinels():
    result = ConfigurationOrchestrator.find_sentinel_paths({"keys": ["_", "_", "real"]})
    assert result == ["$.keys[0]", "$.keys[1]"]


# -- array of objects --


def test_array_of_objects_sentinel_found():
    result = ConfigurationOrchestrator.find_sentinel_paths({"servers": [{"host": "localhost", "password": "_"}]})
    assert result == ["$.servers[0].password"]


def test_array_of_objects_multiple_elements():
    result = ConfigurationOrchestrator.find_sentinel_paths(
        {"servers": [{"password": "_"}, {"password": "real"}, {"password": "_"}]}
    )
    assert result == ["$.servers[0].password", "$.servers[2].password"]


# -- deeply nested mixed structures --


def test_deeply_nested_mixed():
    body = {
        "db": {"host": "localhost", "password": "_"},
        "keys": ["_", "real"],
    }
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert set(result) == {"$.db.password", "$.keys[0]"}


def test_servers_password_mixed():
    body = {"servers": [{"host": "web1", "password": "_"}]}
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert result == ["$.servers[0].password"]


def test_deeply_nested_array_in_dict_in_array():
    body = {"outer": [{"inner": {"secret": "_"}}]}
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert result == ["$.outer[0].inner.secret"]


# -- empty body --


def test_empty_body():
    result = ConfigurationOrchestrator.find_sentinel_paths({})
    assert result == []


# -- body with no sentinels --


def test_body_with_no_sentinels():
    body = {
        "service": "my-service",
        "replicas": 3,
        "enabled": True,
        "tags": ["web", "api"],
        "db": {"host": "localhost", "port": 5432},
    }
    result = ConfigurationOrchestrator.find_sentinel_paths(body)
    assert result == []


# -- sentinel value exclusivity --


def test_underscore_string_only_not_null():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": None})
    assert result == []


def test_underscore_string_only_not_number():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": 0})
    assert result == []


def test_underscore_string_only_not_false():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": False})
    assert result == []


def test_underscore_string_only_not_double_underscore():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": "__"})
    assert result == []


def test_underscore_string_only_not_empty_string():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": ""})
    assert result == []


def test_sentinel_is_exact_string_underscore():
    result = ConfigurationOrchestrator.find_sentinel_paths({"a": "_", "b": "__", "c": None})
    assert result == ["$.a"]


# -- non-leaf objects and arrays are not returned --


def test_dict_value_not_returned_as_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"nested": {"key": "value"}})
    assert result == []


def test_array_value_not_returned_as_sentinel():
    result = ConfigurationOrchestrator.find_sentinel_paths({"list": [1, 2, 3]})
    assert result == []
