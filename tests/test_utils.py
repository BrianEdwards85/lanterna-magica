import pytest

from lanterna_magica.data.utils import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, page_limit, sanitize_search, validate_name
from lanterna_magica.errors import ValidationError


# -- validate_name --


def test_validate_name_allows_plain_text():
    validate_name("traefik")


def test_validate_name_allows_underscores():
    validate_name("db_password")


def test_validate_name_allows_hyphens_and_dots():
    validate_name("my-service.v2")


def test_validate_name_rejects_percent():
    with pytest.raises(ValidationError, match="%"):
        validate_name("bad%name")


def test_validate_name_rejects_backslash():
    with pytest.raises(ValidationError, match=r"\\"):
        validate_name("bad\\name")


def test_validate_name_rejects_percent_at_start():
    with pytest.raises(ValidationError, match="%"):
        validate_name("%leading")


def test_validate_name_rejects_backslash_at_end():
    with pytest.raises(ValidationError, match=r"\\"):
        validate_name("trailing\\")


# -- sanitize_search --


def test_sanitize_search_plain_text():
    assert sanitize_search("traefik") == "traefik"


def test_sanitize_search_escapes_underscore():
    assert sanitize_search("db_password") == r"db\_password"


def test_sanitize_search_strips_percent():
    assert sanitize_search("bad%term") == "badterm"


def test_sanitize_search_strips_backslash():
    assert sanitize_search("bad\\term") == "badterm"


def test_sanitize_search_strips_and_escapes_combined():
    assert sanitize_search("%my_val\\ue") == r"my\_value"


def test_sanitize_search_all_invalid_returns_empty():
    assert sanitize_search("%\\") == ""


def test_sanitize_search_only_underscore():
    assert sanitize_search("_") == r"\_"


# -- page_limit --


def test_page_limit_none_returns_default():
    assert page_limit(None) == DEFAULT_PAGE_SIZE


def test_page_limit_positive_returns_value():
    assert page_limit(10) == 10


def test_page_limit_zero_raises():
    with pytest.raises(ValidationError, match="positive"):
        page_limit(0)


def test_page_limit_negative_raises():
    with pytest.raises(ValidationError, match="positive"):
        page_limit(-1)


def test_page_limit_at_max_returns_value():
    assert page_limit(MAX_PAGE_SIZE) == MAX_PAGE_SIZE


def test_page_limit_exceeds_max_raises():
    with pytest.raises(ValidationError, match="exceed"):
        page_limit(MAX_PAGE_SIZE + 1)
