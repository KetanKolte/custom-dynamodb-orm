"""
Custom DynamoDB ORM: A lightweight, type-safe object-relational mapping layer for Python.

This package provides a clean abstraction over boto3's low-level DynamoDB client,
using Python's native typing system and dataclasses to eliminate boilerplate.

Core Components:
- DynamoModel: Base class for all models with serialize/deserialize
- @dynamo_table: Decorator for attaching table configuration
- DynamoDBAttribute: Type hint metadata for field-to-attribute mapping
- DynamoDbMapper: Generic CRUD operations for any model
- Converters: EnumConverter, EpochMsConverter, JsonConverter for custom types

Example:
    from dataclasses import dataclass
    from typing import Annotated
    from enum import Enum
    
    from custom_dynamodb_orm.attributes import DynamoDBAttribute
    from custom_dynamodb_orm.decorators import dynamo_table
    from custom_dynamodb_orm.model import DynamoModel
    from custom_dynamodb_orm.mapper import DynamoDbMapper
    from custom_dynamodb_orm.converters import EnumConverter
    
    class OrderStatus(Enum):
        PENDING = "pending"
        CONFIRMED = "confirmed"
    
    @dynamo_table(table_name="Orders", hash_key="orderId")
    @dataclass
    class DbOrder(DynamoModel):
        order_id: Annotated[str, DynamoDBAttribute("orderId")] = ""
        status: Annotated[OrderStatus, DynamoDBAttribute("status", converter=EnumConverter)] = OrderStatus.PENDING
    
    class OrderDao(DynamoDbMapper):
        def __init__(self, client):
            super().__init__(client, DbOrder)
    
    # Usage
    import boto3
    client = boto3.client("dynamodb")
    dao = OrderDao(client)
    order = DbOrder(order_id="o-123", status=OrderStatus.CONFIRMED)
    dao.save(order)

See the full blog post and examples at: https://github.com/KetanKolte/custom-dynamodb-orm
"""

from .attributes import (
    DynamoDBAttribute,
    GlobalSecondaryIndexConfig,
    DynamoTableConfig,
)
from .decorators import dynamo_table
from .model import DynamoModel
from .mapper import DynamoDbMapper
from .converters import EnumConverter, EpochMsConverter, JsonConverter

__all__ = [
    "DynamoDBAttribute",
    "GlobalSecondaryIndexConfig",
    "DynamoTableConfig",
    "dynamo_table",
    "DynamoModel",
    "DynamoDbMapper",
    "EnumConverter",
    "EpochMsConverter",
    "JsonConverter",
]

__version__ = "0.1.0"
