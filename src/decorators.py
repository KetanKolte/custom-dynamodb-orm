"""
Class decorator for attaching DynamoDB table configuration to model classes.

The @dynamo_table decorator provides a clean, non-magical way to attach table metadata
without using inheritance or metaclasses. It simply attaches configuration as a class attribute.
"""

from typing import Callable, Optional, Mapping, TypeVar
from .attributes import DynamoTableConfig, GlobalSecondaryIndexConfig

C = TypeVar("C", bound=type)


def dynamo_table(
    *,
    table_name: str,
    hash_key: str,
    range_key: Optional[str] = None,
    global_secondary_index_configs: Optional[Mapping[str,
                                                     GlobalSecondaryIndexConfig]] = None,
) -> Callable[[C], C]:
    """
    Decorator to attach DynamoDB table configuration to a model class.

    Args:
        table_name: The DynamoDB table name
        hash_key: The primary hash (partition) key field name
        range_key: Optional primary sort (range) key field name
        global_secondary_index_configs: Mapping of index name -> GSI configuration

    Returns:
        A decorator function that attaches the config and returns the class unchanged

    Example:
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
            ...
    """
    def decorator(cls: C) -> C:
        cfg = DynamoTableConfig(
            table_name=table_name,
            hash_key=hash_key,
            range_key=range_key,
            global_secondary_index_configs=global_secondary_index_configs or {},
        )
        setattr(cls, "__dynamo_table_config__", cfg)
        return cls

    return decorator
