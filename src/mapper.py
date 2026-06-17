"""
High-level data access object for DynamoDB operations.

DynamoDbMapper orchestrates basic CRUD operations (save, find, delete) for any model
inheriting from DynamoModel. It handles:
- Key construction and serialization
- Delegation to boto3 client methods
- Automatic serialization/deserialization of model instances

Create a specialized DAO for each model by subclassing DynamoDbMapper:

    class OrderDao(DynamoDbMapper):
        def __init__(self, client):
            super().__init__(client, DbOrder)

Then use it for type-safe operations:

    order_dao = OrderDao(dynamodb_client)
    order_dao.save(order)
    found_order = order_dao.find("o-123")
    order_dao.delete("o-123")
"""

from typing import Any, Dict, Optional, Type
from boto3.dynamodb.types import TypeSerializer

from .model import DynamoModel


class DynamoDbMapper:
    """
    Generic data access mapper for DynamoDB operations on a specific model class.

    Handles low-level interaction with the boto3 DynamoDB client while keeping
    business logic isolated in the model classes.

    Attributes:
        _client: The boto3 DynamoDB client
        _model_class: The model class this mapper operates on
        _table_name: The DynamoDB table name
        _hash_key: The primary hash key field name
        _range_key: Optional primary sort key field name
        _gsi_configs: Global Secondary Index configurations
    """

    def __init__(self, dynamodb_client: Any, model_class: Type[DynamoModel]):
        """
        Initialize the mapper with a client and model class.

        Args:
            dynamodb_client: A boto3 DynamoDB client (resource or low-level)
            model_class: A class inheriting from DynamoModel (must have @dynamo_table)

        Raises:
            ValueError: If model_class is not a DynamoModel or lacks @dynamo_table
        """
        schema_config = model_class.get_schema()
        self._client = dynamodb_client
        self._model_class = model_class
        self._table_name = schema_config.table_name
        self._hash_key = schema_config.hash_key
        self._range_key = schema_config.range_key
        self._gsi_configs = schema_config.global_secondary_index_configs
        self._serializer = TypeSerializer()

    def _build_key(self, hash_val: Any, range_val: Optional[Any] = None) -> Dict[str, Any]:
        """
        Construct a DynamoDB key structure from hash and optional range values.

        Args:
            hash_val: The hash key value
            range_val: Optional range key value (required if model has range_key)

        Returns:
            Dict mapping key field names to their values

        Example:
            _build_key("o-123", "u-456")
            # -> {"orderId": "o-123", "createdAt": "u-456"}
        """
        key_structure = {self._hash_key: hash_val}
        if self._range_key and range_val:
            key_structure[self._range_key] = range_val
        return key_structure

    def save(self, item: DynamoModel) -> None:
        """
        Save (insert or overwrite) a model instance to DynamoDB.

        Uses put_item, which means the operation is idempotent: running it
        multiple times with the same key will overwrite the item.

        Args:
            item: An instance of self._model_class

        Raises:
            Exception: If the boto3 put_item call fails

        Example:
            order = DbOrder(order_id="o-123", user_id="u-456")
            order_dao.save(order)
        """
        self._client.put_item(TableName=self._table_name,
                              Item=item.serialize())

    def find(
        self, hash_key_value: Any, range_key_value: Optional[Any] = None
    ) -> Optional[DynamoModel]:
        """
        Retrieve a single item from DynamoDB by primary key.

        Returns None if the item does not exist (not an error condition).

        Args:
            hash_key_value: The hash key value to find
            range_key_value: Optional range key value (required if model has range_key)

        Returns:
            An instance of self._model_class, or None if not found

        Raises:
            Exception: If the boto3 get_item call fails

        Example:
            order = order_dao.find("o-123")
            if order:
                print(f"Found order for user {order.user_id}")
        """
        key = self._build_key(hash_key_value, range_key_value)
        wire_key = {k: self._serializer.serialize(v) for k, v in key.items()}

        response = self._client.get_item(
            TableName=self._table_name, Key=wire_key)
        item_record = response.get("Item")
        return self._model_class.deserialize(item_record) if item_record else None

    def delete(self, hash_key_value: Any, range_key_value: Optional[Any] = None) -> None:
        """
        Delete an item from DynamoDB by primary key.

        Deletion is idempotent: deleting a non-existent key does not raise an error.

        Args:
            hash_key_value: The hash key value to delete
            range_key_value: Optional range key value (required if model has range_key)

        Raises:
            Exception: If the boto3 delete_item call fails

        Example:
            order_dao.delete("o-123")  # Item is now gone
        """
        key = self._build_key(hash_key_value, range_key_value)
        wire_key = {k: self._serializer.serialize(v) for k, v in key.items()}
        self._client.delete_item(TableName=self._table_name, Key=wire_key)
