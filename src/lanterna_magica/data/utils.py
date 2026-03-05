import json
import re
from base64 import b64decode, b64encode
from pathlib import Path

import aiosql

SQL_DIR = Path(__file__).parent.parent / "sql"

queries = aiosql.from_path(str(SQL_DIR), "asyncpg")

SENTINEL_UUID = "00000000-0000-0000-0000-000000000000"

DEFAULT_PAGE_SIZE = 25


def page_limit(first: int | None) -> int:
    if first is not None and first < 1:
        raise ValueError("first must be a positive integer")
    return first if first is not None else DEFAULT_PAGE_SIZE

INVALID_NAME_CHARS = re.compile(r'[%\\]')


def validate_name(name: str) -> None:
    if INVALID_NAME_CHARS.search(name):
        raise ValueError("Name must not contain '%' or '\\' characters")


def sanitize_search(search: str) -> str:
    cleaned = INVALID_NAME_CHARS.sub('', search)
    return cleaned.replace('_', r'\_')


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
