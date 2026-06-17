"""
DynamoDB table and attribute configuration metadata.

This module defines the metadata classes used to describe DynamoDB tables and their attributes.
- DynamoDBAttribute: Embeds schema info (DB alias, type converter) into field type hints
- DynamoTableConfig: Describes table structure (name, keys, GSI configs)
- GlobalSecondaryIndexConfig: Describes a Global Secondary Index
"""

from dataclasses import dataclass, field
from typing import Optional, Mapping, Type


@dataclass(frozen=True)
class DynamoDBAttribute:
    """
    Metadata attached to a type-hinted field via typing.Annotated.

    Attributes:
        alias: The DynamoDB attribute name on the wire (e.g., "orderId")
        converter: Optional custom converter class for non-primitive types (e.g., EnumConverter)

    Example:
        user_id: Annotated[str, DynamoDBAttribute("userId")]
        status: Annotated[OrderStatus, DynamoDBAttribute("status", converter=EnumConverter)]
    """
    alias: str
    converter: Optional[Type] = None


@dataclass(frozen=True)
class GlobalSecondaryIndexConfig:
    """
    Configuration for a DynamoDB Global Secondary Index (GSI).

    Attributes:
        index_name: The name of the GSI
        hash_key: The hash (partition) key field name for this index
        range_key: Optional sort (range) key field name for this index

    Example:
        @dynamo_table(
            table_name="Orders",
            hash_key="orderId",
            global_secondary_index_configs={
                "by-user-index": GlobalSecondaryIndexConfig(
                    index_name="by-user-index",
                    hash_key="userId",
                    range_key="createdAt",
                )
            },
        )
        @dataclass
        class DbOrder(DynamoModel):
            ...
    """
    index_name: str
    hash_key: str
    range_key: Optional[str] = None


@dataclass(frozen=True)
class DynamoTableConfig:
    """
    Complete table configuration attached by the @dynamo_table decorator.

    Attributes:
        table_name: The DynamoDB table name
        hash_key: The primary hash (partition) key field name
        range_key: Optional primary sort (range) key field name
        global_secondary_index_configs: Mapping of index names to their GSI configurations

    Example:
        # This is typically created automatically by @dynamo_table decorator:
        @dynamo_table(
            table_name="Orders",
            hash_key="orderId",
            range_key="createdAt",
        )
        @dataclass
        class DbOrder(DynamoModel):
            ...

        # To access the config from a model:
        schema_config = DbOrder.get_schema()
        print(schema_config.table_name)    # "Orders"
        print(schema_config.hash_key)      # "orderId"
        print(schema_config.range_key)     # "createdAt"
    """
    table_name: str
    hash_key: str
    range_key: Optional[str] = None
    global_secondary_index_configs: Mapping[str, GlobalSecondaryIndexConfig] = field(
        default_factory=dict
    )
