"""
Base model class for DynamoDB records.

DynamoModel is the foundation of the ORM. It provides:
- get_schema(): Retrieves table configuration attached by @dynamo_table
- serialize(): Converts a model instance to low-level DynamoDB wire format
- deserialize(): Reconstructs a model instance from wire format

Models should inherit from DynamoModel and be decorated with @dynamo_table:

    @dynamo_table(table_name="Orders", hash_key="orderId")
    @dataclass
    class DbOrder(DynamoModel):
        order_id: Annotated[str, DynamoDBAttribute("orderId")]
        ...

The serialize/deserialize cycle is transparent to the user and fully automated.
"""

from typing import Any, Dict, Optional, Type, TypeVar
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

from .attributes import DynamoTableConfig
from .serialization import _cached_serialization_map, _cached_deserialization_map

T = TypeVar("T", bound="DynamoModel")

# Reusable boto3 serializers (thread-safe, stateless)
_SERIALIZER = TypeSerializer()
_DESERIALIZER = TypeDeserializer()


class DynamoModel:
    """
    Base class for DynamoDB model classes.

    Provides schema retrieval and serialization/deserialization methods.
    Subclasses should use @dynamo_table decorator and @dataclass.

    Example:
        @dynamo_table(table_name="Orders", hash_key="orderId")
        @dataclass
        class DbOrder(DynamoModel):
            order_id: Annotated[str, DynamoDBAttribute("orderId")] = ""
    """

    @classmethod
    def get_schema(cls) -> DynamoTableConfig:
        """
        Retrieve the table configuration attached by the @dynamo_table decorator.

        Returns:
            DynamoTableConfig with table name, keys, and index configurations

        Raises:
            ValueError: If class is missing @dynamo_table decorator
        """
        config_obj = getattr(cls, "__dynamo_table_config__", None)
        if not config_obj:
            raise ValueError(
                f"Class {cls.__name__} is missing the @dynamo_table decorator. "
                f"Models must be decorated with @dynamo_table(table_name=..., hash_key=...)."
            )
        return config_obj

    def serialize(self) -> Dict[str, Any]:
        """
        Marshal this model instance into low-level DynamoDB wire format.

        The wire format uses DynamoDB's type descriptors:
            {"S": "string_value"}
            {"N": "42"}
            {"BOOL": true}
            etc.

        Fields without DynamoDBAttribute annotations are skipped.
        Empty strings and None values are excluded from the output (sparse format).
        Custom converters are applied as needed.

        Returns:
            Dict[str, Any] ready to be passed to boto3's put_item, update_item, etc.

        Example:
            order = DbOrder(order_id="o-123", user_id="u-456")
            wire_format = order.serialize()
            # Result: {"orderId": {"S": "o-123"}, "userId": {"S": "u-456"}}
        """
        dynamo_record = {}
        serialization_rules = _cached_serialization_map(type(self))

        for field_name, (db_alias, converter_class, core_type) in serialization_rules.items():
            field_value = getattr(self, field_name, None)

            # Avoid sparse nulls and empty strings in the database
            if field_value is None or field_value == "":
                continue

            # Apply custom converter if one is registered
            transformed_value = (
                converter_class.convert(
                    field_value) if converter_class else field_value
            )

            # Use boto3's TypeSerializer to convert to DynamoDB wire format
            dynamo_record[db_alias] = _SERIALIZER.serialize(transformed_value)

        return dynamo_record

    @classmethod
    def deserialize(cls: Type[T], item_record: Dict[str, Any]) -> T:
        """
        Unmarshal a raw DynamoDB wire record back into a strongly-typed model instance.

        Wire format is expected as returned by boto3's get_item, query, scan, etc.:
            {"orderId": {"S": "o-123"}, "userId": {"S": "u-456"}}

        Unknown attributes (not mapped in the model) are silently ignored,
        allowing graceful schema evolution when the database schema changes.

        Custom converters are applied to restore original Python types.

        Args:
            item_record: Dict in DynamoDB wire format

        Returns:
            An instance of cls

        Raises:
            TypeError: If constructor arguments cannot be satisfied

        Example:
            wire_format = {"orderId": {"S": "o-123"}, "userId": {"S": "u-456"}}
            order = DbOrder.deserialize(wire_format)
            # Result: DbOrder(order_id="o-123", user_id="u-456")
        """
        attr_registry = _cached_deserialization_map(cls)
        constructor_args = {}

        for attr_name, db_value in item_record.items():
            # Look up the Python field name for this DynamoDB attribute
            field_metadata = attr_registry.get(attr_name)
            if field_metadata is None:
                # Silently ignore unmapped attributes for schema evolution
                continue

            field_name, converter_class, core_type = field_metadata

            # Use boto3's TypeDeserializer to convert from wire format
            unmarshalled_value = _DESERIALIZER.deserialize(db_value)

            # Apply custom converter if one is registered
            if converter_class:
                constructor_args[field_name] = converter_class.unconvert(
                    unmarshalled_value, core_type)
            else:
                constructor_args[field_name] = unmarshalled_value

        return cls(**constructor_args)
