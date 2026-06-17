"""
Type converters for serializing/deserializing non-primitive types.

DynamoDB natively supports only a few primitive types (strings, numbers, binary, booleans, etc.).
Complex types like enums, datetimes, or custom objects need to be converted to/from primitives
before transmission. Each converter implements a simple interface:

    - convert(python_value) -> serializable_value
    - unconvert(wire_value, field_type) -> python_value

This keeps conversion logic decoupled from the core serialization orchestration.
"""

from typing import Any, Optional
from enum import Enum
from datetime import datetime, timezone
import json


class EnumConverter:
    """
    Converts Python Enum members to their string names for storage.

    Stores only the Enum member's .name attribute (e.g., OrderStatus.PENDING -> "PENDING").
    Handles None gracefully for Optional enum fields.

    Example:
        @dataclass
        class DbOrder(DynamoModel):
            status: Annotated[OrderStatus, DynamoDBAttribute("status", converter=EnumConverter)]

        order = DbOrder(status=OrderStatus.PENDING)
        order.serialize()  # -> {"status": {"S": "PENDING"}}
    """

    @staticmethod
    def convert(v: Any) -> Optional[str]:
        """
        Convert an Enum member to its name string.

        Args:
            v: An Enum member or None

        Returns:
            The Enum member's .name, or None if v is None
        """
        return v.name if v is not None else None

    @staticmethod
    def unconvert(wire_value: Any, enum_type: Any) -> Any:
        """
        Convert a name string back to an Enum member.

        Args:
            wire_value: A string (the Enum member name)
            enum_type: The Enum class (e.g., OrderStatus)

        Returns:
            The Enum member, or None if wire_value is None
        """
        return enum_type[wire_value] if wire_value is not None else None


class EpochMsConverter:
    """
    Converts Python datetime objects to/from epoch milliseconds.

    Stores datetime objects as integer milliseconds since Unix epoch (UTC).
    Always returns datetimes in UTC timezone.

    Example:
        @dataclass
        class DbOrder(DynamoModel):
            created_at: Annotated[datetime, DynamoDBAttribute("createdAt", converter=EpochMsConverter)]

        order = DbOrder(created_at=datetime.now(timezone.utc))
        order.serialize()  # -> {"createdAt": {"N": "1719172343000"}}
    """

    @staticmethod
    def convert(v: datetime) -> int:
        """
        Convert a datetime to epoch milliseconds.

        Args:
            v: A datetime object

        Returns:
            Milliseconds since Unix epoch as an integer
        """
        return int(v.timestamp() * 1000)

    @staticmethod
    def unconvert(wire_value: Any, _field_type: Any) -> datetime:
        """
        Convert epoch milliseconds back to a datetime (UTC).

        Args:
            wire_value: Integer milliseconds since Unix epoch
            _field_type: Unused (included for interface consistency)

        Returns:
            A datetime object in UTC timezone
        """
        return datetime.fromtimestamp(wire_value / 1000, tz=timezone.utc)


class JsonConverter:
    """
    Converts arbitrary Python objects to/from JSON strings.

    Useful for storing dictionaries, lists, or other JSON-serializable objects
    as DynamoDB strings. The wire format is a JSON string; deserialization
    reconstructs the Python object.

    Example:
        @dataclass
        class DbOrder(DynamoModel):
            metadata: Annotated[dict, DynamoDBAttribute("metadata", converter=JsonConverter)]

        order = DbOrder(metadata={"channel": "web", "discount": 0.1})
        order.serialize()  # -> {"metadata": {"S": "{\"channel\": \"web\", \"discount\": 0.1}"}}
    """

    @staticmethod
    def convert(v: Any) -> str:
        """
        Convert a Python object to a JSON string.

        Args:
            v: Any JSON-serializable Python object

        Returns:
            A JSON string representation
        """
        return json.dumps(v)

    @staticmethod
    def unconvert(wire_value: str, _field_type: Any) -> Any:
        """
        Convert a JSON string back to a Python object.

        Args:
            wire_value: A JSON string
            _field_type: Unused (included for interface consistency)

        Returns:
            The deserialized Python object
        """
        return json.loads(wire_value)
