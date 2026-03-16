from datetime import datetime


def parse_dt(iso_string):
    return datetime.fromisoformat(iso_string)


def nodes(edges):
    return [e["node"] for e in edges]
