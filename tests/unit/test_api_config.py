import pytest
import tomli_w

from lanterna_magica.orchestrator.configuration import _sanitize_for_toml

# ---------------------------------------------------------------------------
# _sanitize_for_toml -dict behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sanitize_dict_drops_none_values():
    result = _sanitize_for_toml({"a": 1, "b": None, "c": "hello"})
    assert result == {"a": 1, "c": "hello"}
    assert "b" not in result


@pytest.mark.unit
def test_sanitize_dict_all_none_values():
    result = _sanitize_for_toml({"x": None, "y": None})
    assert result == {}


@pytest.mark.unit
def test_sanitize_dict_no_none_values_unchanged():
    original = {"host": "localhost", "port": 5432}
    result = _sanitize_for_toml(original)
    assert result == original


@pytest.mark.unit
def test_sanitize_dict_nested_none_dropped():
    result = _sanitize_for_toml({"outer": {"inner_none": None, "keep": 42}})
    assert result == {"outer": {"keep": 42}}


# ---------------------------------------------------------------------------
# _sanitize_for_toml -list behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sanitize_list_drops_none_elements():
    result = _sanitize_for_toml(["a", None, "b", None])
    assert result == ["a", "b"]


@pytest.mark.unit
def test_sanitize_list_all_none_becomes_empty():
    result = _sanitize_for_toml([None, None])
    assert result == []


@pytest.mark.unit
def test_sanitize_list_homogeneous_integers_unchanged():
    result = _sanitize_for_toml([1, 2, 3])
    assert result == [1, 2, 3]


@pytest.mark.unit
def test_sanitize_list_mixed_after_none_removal_none_dropped():
    # After dropping None: [1, "hello"] — passed through as-is (no stringification)
    result = _sanitize_for_toml([1, None, "hello"])
    assert result == [1, "hello"]


@pytest.mark.unit
def test_sanitize_list_bool_int_unchanged():
    # [True, 1] must pass through unchanged
    result = _sanitize_for_toml([True, 1])
    assert result == [True, 1]


@pytest.mark.unit
def test_sanitize_list_dicts_inside_list_recursed():
    result = _sanitize_for_toml([{"a": None, "b": 2}])
    assert result == [{"b": 2}]


# ---------------------------------------------------------------------------
# _sanitize_for_toml -scalar passthrough
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sanitize_scalar_int():
    assert _sanitize_for_toml(42) == 42


@pytest.mark.unit
def test_sanitize_scalar_string():
    assert _sanitize_for_toml("hello") == "hello"


@pytest.mark.unit
def test_sanitize_scalar_bool():
    assert _sanitize_for_toml(True) is True


# ---------------------------------------------------------------------------
# Integration with tomli_w: configs that previously caused TypeError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_toml_serialization_with_null_values():
    """tomli_w.dumps must not raise for a config containing None values."""
    config = {
        "database": {
            "host": "localhost",
            "password": None,  # TOML has no null — must be dropped
            "port": 5432,
        }
    }
    sanitized = _sanitize_for_toml(config)
    toml_str = tomli_w.dumps(sanitized)
    assert "host" in toml_str
    assert "port" in toml_str
    assert "password" not in toml_str


@pytest.mark.unit
def test_toml_serialization_combined_nulls():
    """End-to-end: config with null values serializes to valid TOML without error."""
    config = {
        "service": "my-service",
        "optional": None,
        "tags": ["alpha", "beta"],
        "nested": {
            "key": None,
            "value": 100,
        },
    }
    sanitized = _sanitize_for_toml(config)
    # Must not raise
    toml_str = tomli_w.dumps(sanitized)
    assert "service" in toml_str
    assert "optional" not in toml_str
    assert "value" in toml_str
    assert "key" not in toml_str
    assert "alpha" in toml_str
