"""
Example: Order model demonstrating the full DynamoDB ORM in action.

This module shows how to define a real-world domain model (Order) using the ORM,
including handling of enums, timestamps, nested objects, and optional fields.

Key concepts demonstrated:
1. Enum fields (OrderStatus) converted to strings
2. Datetime fields converted to epoch milliseconds
3. Nested objects (metadata dict) converted to JSON
4. Optional fields that may be sparse in the database
5. Specialized DAO for type-safe operations
"""

from enum import Enum
from typing import Annotated, Optional
from dataclasses import dataclass
from datetime import datetime

from .attributes import DynamoDBAttribute, GlobalSecondaryIndexConfig
from .converters import EnumConverter, EpochMsConverter, JsonConverter
from .decorators import dynamo_table
from .model import DynamoModel
from .mapper import DynamoDbMapper


class OrderStatus(Enum):
    """Enumeration of possible order states."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"


@dynamo_table(
    table_name="ProductionOrders",
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
    """
    A domain model for orders stored in DynamoDB.

    Demonstrates:
    - String fields (order_id, user_id, note)
    - Enum field (status) with EnumConverter
    - Datetime field (created_at) with EpochMsConverter
    - Dict field (metadata) with JsonConverter
    - Optional fields (all except order_id and user_id)

    Attributes:
        order_id: Unique order identifier (partition key)
        user_id: ID of the user who placed the order
        status: Current order status (PENDING, CONFIRMED, SHIPPED)
        created_at: Timestamp when the order was created
        metadata: Arbitrary metadata (e.g., channel, discount info)
        note: Optional delivery notes
    """

    order_id: Annotated[str, DynamoDBAttribute("orderId")] = ""
    user_id: Annotated[str, DynamoDBAttribute("userId")] = ""
    status: Annotated[OrderStatus, DynamoDBAttribute("status", converter=EnumConverter)] = (
        OrderStatus.PENDING
    )
    created_at: Annotated[Optional[datetime], DynamoDBAttribute(
        "createdAt", converter=EpochMsConverter)] = None
    metadata: Annotated[Optional[dict], DynamoDBAttribute(
        "metadata", converter=JsonConverter)] = None
    note: Annotated[Optional[str], DynamoDBAttribute("note")] = None


class OrderDao(DynamoDbMapper):
    """
    Data Access Object for Order operations.

    Provides type-safe CRUD methods for DbOrder instances.

    Usage:
        client = boto3.client("dynamodb", region_name="us-east-1")
        order_dao = OrderDao(client)
        order_dao.save(order)
        found = order_dao.find("o-123")
        order_dao.delete("o-123")
    """

    def __init__(self, client):
        """
        Initialize the DAO with a boto3 DynamoDB client.

        Args:
            client: A boto3 DynamoDB client
        """
        super().__init__(client, DbOrder)
