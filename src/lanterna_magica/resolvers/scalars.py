from datetime import datetime

from ariadne import ScalarType

datetime_scalar = ScalarType("DateTime")


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
