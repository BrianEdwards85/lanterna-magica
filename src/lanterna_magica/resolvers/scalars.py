from datetime import datetime

from ariadne import ScalarType

datetime_scalar = ScalarType("DateTime")
json_scalar = ScalarType("JSON")


@datetime_scalar.serializer
def serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@datetime_scalar.value_parser
def parse_datetime(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


@json_scalar.serializer
def serialize_json(value):
    return value


@json_scalar.value_parser
def parse_json(value):
    return value
