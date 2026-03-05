from base64 import b64decode, b64encode
from pathlib import Path

import aiosql

SQL_DIR = Path(__file__).parent.parent / "sql"

queries = aiosql.from_path(str(SQL_DIR), "asyncpg")

DEFAULT_PAGE_SIZE = 25


def encode_cursor(value: str) -> str:
    return b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    return b64decode(cursor.encode()).decode()


def build_connection(rows: list[dict], cursor_key: str, limit: int) -> dict:
    has_next = len(rows) > limit
    nodes = rows[:limit]
    edges = [
        {"cursor": encode_cursor(str(row[cursor_key])), "node": row} for row in nodes
    ]
    return {
        "edges": edges,
        "page_info": {
            "has_next_page": has_next,
            "end_cursor": edges[-1]["cursor"] if edges else None,
        },
    }
