import hashlib
import json
import re
from base64 import b64decode, b64encode
from pathlib import Path

import aiosql

from lanterna_magica.errors import NotFoundError, ValidationError

SQL_DIR = Path(__file__).parent.parent / "sql"

queries = aiosql.from_path(str(SQL_DIR), "asyncpg")

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def compute_scope_hash(dimension_ids: list[str]) -> str:
    joined = ",".join(sorted(dimension_ids))
    hex_digest = hashlib.md5(joined.encode()).hexdigest()
    return f"{hex_digest[:8]}-{hex_digest[8:12]}-{hex_digest[12:16]}-{hex_digest[16:20]}-{hex_digest[20:]}"


def page_limit(first: int | None) -> int:
    if first is not None and first < 1:
        raise ValidationError("first must be a positive integer")
    if first is not None and first > MAX_PAGE_SIZE:
        raise ValidationError(f"first must not exceed {MAX_PAGE_SIZE}")
    return first if first is not None else DEFAULT_PAGE_SIZE

INVALID_NAME_CHARS = re.compile(r'[%\\]')


def validate_name(name: str) -> None:
    if INVALID_NAME_CHARS.search(name):
        raise ValidationError("Name must not contain '%' or '\\' characters")


def sanitize_search(search: str) -> str:
    # 1. Strip chars that are dangerous in ILIKE patterns (% and \)
    cleaned = re.sub(r'[%\\]', '', search)
    # 2. Escape _ so it matches literally instead of acting as single-char wildcard
    return cleaned.replace('_', r'\_')


async def require_row(query_fn, error_msg: str, *args, **kwargs) -> dict:
    row = await query_fn(*args, **kwargs)
    if not row:
        raise NotFoundError(error_msg)
    return dict(row)


class InvalidCursorError(Exception):
    pass


def encode_cursor(value: str, *, search: str | None = None) -> str:
    payload = json.dumps({"id": value, "search": search or ""}, separators=(",", ":"))
    return b64encode(payload.encode()).decode()


def decode_cursor(cursor: str, *, search: str | None = None) -> str:
    payload = json.loads(b64decode(cursor.encode()).decode())
    cursor_search = payload.get("search", "")
    expected_search = search or ""
    if cursor_search != expected_search:
        raise InvalidCursorError("Cursor was created with a different search query")
    return payload["id"]


def build_connection(
    rows: list[dict], cursor_key: str, limit: int, *, search: str | None = None
) -> dict:
    has_next = len(rows) > limit
    nodes = rows[:limit]
    edges = [
        {
            "cursor": encode_cursor(str(row[cursor_key]), search=search),
            "node": row,
        }
        for row in nodes
    ]
    return {
        "edges": edges,
        "page_info": {
            "has_next_page": has_next,
            "end_cursor": edges[-1]["cursor"] if edges else None,
        },
    }
