# Custom DynamoDB ORM

A lightweight, type-safe object-relational mapping (ORM) layer for Amazon DynamoDB in Python. Built using native Python typing, dataclasses, and class decorators—no metaclasses, no external frameworks.

## Why This ORM?

When working with DynamoDB and boto3, you quickly face tedious boilerplate:
- Every `put_item` and `get_item` requires verbose type descriptors (`{"S": "value"}`, `{"N": "42"}`)
- Field names are scattered as string literals throughout your codebase
- Adding a column means modifying serialization and deserialization code in multiple places
- No type safety for query results

This ORM eliminates that friction by making **your data model the single source of truth**.

## Key Features

✨ **Minimal Dependencies** — Only requires `boto3`  
🔒 **Type-Safe** — Full typing support with Python 3.12+  
🏗️ **No Metaclasses** — Uses standard dataclasses and simple decorators  
🎯 **Clean Code** — Define schema once, serialize/deserialize automatically  
🔄 **Extensible** — Custom type converters for enums, dates, nested objects  
📦 **Schema Evolution** — Gracefully ignores unknown attributes when reading  

## Installation

```bash
pip install custom-dynamodb-orm
```

Or install from source:

```bash
git clone https://github.com/KetanKolte/custom-dynamodb-orm.git
cd custom-dynamodb-orm
pip install -e .
```

## Quick Start

### 1. Define Your Model

```python
from dataclasses import dataclass
from typing import Annotated, Optional
from enum import Enum
from datetime import datetime

from custom_dynamodb_orm import (
    DynamoModel,
    dynamo_table,
    DynamoDBAttribute,
    EnumConverter,
    EpochMsConverter,
)

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"

@dynamo_table(table_name="Orders", hash_key="orderId")
@dataclass
class DbOrder(DynamoModel):
    order_id: Annotated[str, DynamoDBAttribute("orderId")] = ""
    user_id: Annotated[str, DynamoDBAttribute("userId")] = ""
    status: Annotated[OrderStatus, DynamoDBAttribute("status", converter=EnumConverter)] = OrderStatus.PENDING
    created_at: Annotated[Optional[datetime], DynamoDBAttribute("createdAt", converter=EpochMsConverter)] = None
```

See [src/order_example.py](src/order_example.py) for the full example.

### 2. Create a Data Access Object (DAO)

```python
from custom_dynamodb_orm import DynamoDbMapper

class OrderDao(DynamoDbMapper):
    def __init__(self, client):
        super().__init__(client, DbOrder)
```

### 3. Use It

```python
import boto3

client = boto3.client("dynamodb", region_name="us-east-1")
dao = OrderDao(client)

# Save an order
order = DbOrder(
    order_id="o-123",
    user_id="u-456",
    status=OrderStatus.CONFIRMED,
    created_at=datetime.now(timezone.utc),
)
dao.save(order)

# Find an order
found = dao.find("o-123")
print(found.status)  # Output: OrderStatus.CONFIRMED

# Delete an order
dao.delete("o-123")
```

## Project Structure

```
src/
├── __init__.py              # Package exports
├── attributes.py            # DynamoDBAttribute, DynamoTableConfig
├── decorators.py            # @dynamo_table decorator
├── model.py                 # DynamoModel base class (serialize/deserialize)
├── serialization.py         # Reflection & caching utilities
├── converters.py            # EnumConverter, EpochMsConverter, JsonConverter
├── mapper.py                # DynamoDbMapper for CRUD operations
└── order_example.py         # Example: Order model with all field types
```

## Core Concepts

### Models: DynamoModel + @dynamo_table

Every model inherits from `DynamoModel` and is decorated with `@dynamo_table`:

```python
@dynamo_table(
    table_name="Orders",
    hash_key="orderId",
    range_key="createdAt",  # optional
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
```

### Fields: Annotated + DynamoDBAttribute

Field schema lives directly in the type hint using `Annotated`:

```python
# Simple string field
order_id: Annotated[str, DynamoDBAttribute("orderId")] = ""

# Enum field with automatic conversion
status: Annotated[OrderStatus, DynamoDBAttribute("status", converter=EnumConverter)] = OrderStatus.PENDING

# Datetime field stored as epoch milliseconds
created_at: Annotated[datetime, DynamoDBAttribute("createdAt", converter=EpochMsConverter)] = None

# Dict field stored as JSON string
metadata: Annotated[dict, DynamoDBAttribute("metadata", converter=JsonConverter)] = None

# Field without DynamoDBAttribute is excluded from serialization
internal_state: str = ""  # Not persisted
```

### Converters: Handle Complex Types

Built-in converters handle non-primitive types:

```python
# Enums → strings
class EnumConverter:
    @staticmethod
    def convert(v):
        return v.name if v else None
    
    @staticmethod
    def unconvert(wire_value, enum_type):
        return enum_type[wire_value] if wire_value else None

# Datetimes → epoch milliseconds
class EpochMsConverter:
    @staticmethod
    def convert(v: datetime) -> int:
        return int(v.timestamp() * 1000)
    
    @staticmethod
    def unconvert(wire_value: int, _) -> datetime:
        return datetime.fromtimestamp(wire_value / 1000, tz=timezone.utc)

# Dicts/Lists → JSON strings
class JsonConverter:
    @staticmethod
    def convert(v):
        return json.dumps(v)
    
    @staticmethod
    def unconvert(wire_value, _):
        return json.loads(wire_value)
```

Create custom converters by following the same interface.

### Mapper: DynamoDbMapper for CRUD

The `DynamoDbMapper` provides type-safe access to DynamoDB operations:

```python
dao = OrderDao(dynamodb_client)

# CREATE / UPDATE
dao.save(order)

# READ
found = dao.find("o-123")  # Returns DbOrder or None
found = dao.find("o-123", "2026-06-01")  # With range key

# DELETE
dao.delete("o-123")
dao.delete("o-123", "2026-06-01")  # With range key
```

## Blog Post

For a deep dive into the design, architecture, and implementation details, see [blog.md](blog.md).

Topics covered:
- The problem with raw boto3
- Design goals and architecture overview
- Step-by-step implementation (schema mapping, decorators, reflection, caching, serialization, converters)
- Real-world examples

## Python Version

Requires **Python 3.12+** for full `typing.Annotated` support and modern type hint features.

## Dependencies

- `boto3>=1.26.0` — AWS SDK for Python

## License

Apache License 2.0 — see [LICENSE](LICENSE)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## References

- [boto3 DynamoDB Type Serialization](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/dynamodb.html)
- [Python typing.Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated)
- [Dataclasses](https://docs.python.org/3/library/dataclasses.html)
