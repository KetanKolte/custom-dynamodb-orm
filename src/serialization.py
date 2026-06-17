"""
Reflection utilities and caching functions for schema inspection.

This module handles the runtime inspection of dataclass fields to extract DynamoDB schema
metadata. It uses typing.get_origin and typing.get_args to inspect Annotated type hints
and extracts DynamoDBAttribute metadata.

Key functions:
- _unwrap_underlying_type: Peels back Optional, Union, and Annotated wrappers
- _parse_field_metadata: Extracts DynamoDBAttribute from a dataclass field
- _cached_serialization_map: Caches field metadata for efficient serialization
- _cached_deserialization_map: Caches field metadata for efficient deserialization
"""

import dataclasses
import functools
from typing import Any, Dict, Optional, Tuple, Union, get_origin, get_args, Annotated

from .attributes import DynamoDBAttribute


def _unwrap_underlying_type(type_hint: Any) -> Any:
    """
    Recursively unwrap complex type wrappers to find the underlying type.

    Handles:
    - Annotated[T, ...] -> unwraps to find T
    - Optional[T] (Union[T, None]) -> unwraps to T
    - Union[T, None] -> unwraps to T

    Args:
        type_hint: A potentially wrapped type hint

    Returns:
        The innermost non-wrapper type

    Examples (Input -> Output):
        1) Input:
               Annotated[str, DynamoDBAttribute("userId")]
           Output:
               str
           Meaning:
               Remove Annotated wrapper and keep the base type.

        2) Input:
               Optional[datetime]
           Output:
               datetime
           Meaning:
               Remove Optional (Union[datetime, None]) and keep the non-None type.

        3) Input:
               Optional[Annotated[dict, DynamoDBAttribute("metadata")]]
           Output:
               dict
           Meaning:
               Recursively remove both Optional and Annotated wrappers.

        4) Input:
               int
           Output:
               int
           Meaning:
               Type is already concrete, so it is returned unchanged.
    """
    origin_type = get_origin(type_hint)

    if origin_type is Annotated:
        # Annotated[T, ...] has T as first arg
        return _unwrap_underlying_type(get_args(type_hint)[0])

    if origin_type is Union:
        # Filter out NoneType to handle Optional safely
        clean_types = [arg for arg in get_args(
            type_hint) if arg is not type(None)]
        if len(clean_types) == 1:
            return _unwrap_underlying_type(clean_types[0])

    return type_hint


def _parse_field_metadata(model_field: dataclasses.Field) -> Optional[Tuple[str, Optional[type], Any]]:
    """
    Extract DynamoDBAttribute metadata from a dataclass field's type hint.

    Returns None if the field is not annotated with DynamoDBAttribute (excluded from serialization).
    Returns a tuple of (db_alias, converter_class, underlying_type) if found.

    Args:
        model_field: A dataclass field

    Returns:
        (db_alias, converter_class, underlying_type) or None if not a DynamoDB field

    Return tuple guide:
        - db_alias: DynamoDB attribute name on the wire (for example, "createdAt")
        - converter_class: Converter class used for transform/untransform.
          None means the value is handled directly as a primitive.
        - underlying_type: Final unwrapped Python type used during deserialization.

    Examples (Input field -> Return value):
        1) Input field:
               order_id: Annotated[str, DynamoDBAttribute("orderId")]
           Return:
               ("orderId", None, str)
           Meaning:
               Store/read under "orderId", no converter needed, value is treated as str.

        2) Input field:
               status: Annotated[OrderStatus, DynamoDBAttribute("status", converter=EnumConverter)]
           Return:
               ("status", EnumConverter, OrderStatus)
           Meaning:
               Use EnumConverter to convert OrderStatus to/from DynamoDB value.

        3) Input field:
               created_at: Annotated[Optional[datetime], DynamoDBAttribute("createdAt", converter=EpochMsConverter)]
           Return:
               ("createdAt", EpochMsConverter, datetime)
           Meaning:
               Alias is "createdAt" and final core type is datetime after unwrapping Optional.

        4) Input field:
               metadata: Annotated[Optional[dict], DynamoDBAttribute("metadata", converter=JsonConverter)]
           Return:
               ("metadata", JsonConverter, dict)
           Meaning:
               Use JsonConverter and treat the core type as dict.

        5) Input field:
               internal_state: str
           Return:
               None
           Meaning:
               Field is not mapped to DynamoDB because no DynamoDBAttribute metadata exists.

    Warning:
        This function uses typing.get_args which requires get_type_hints() to be called
        with include_extras=True to handle Annotated correctly.
    """
    # Use typing.get_type_hints with include_extras=True to properly handle Annotated
    # This avoids the __future__ annotations pitfall where lazy evaluation turns hints into strings
    try:
        # get_origin checks if the type_hint is an Annotated generic
        if get_origin(model_field.type) is not Annotated:
            return None

        # get_args returns (base_type, metadata_0, metadata_1, ...)
        args = get_args(model_field.type)
        base_type = args[0]

        # Search through metadata for DynamoDBAttribute
        for annotation_meta in args[1:]:
            if isinstance(annotation_meta, DynamoDBAttribute):
                underlying_type = _unwrap_underlying_type(model_field.type)
                return annotation_meta.alias, annotation_meta.converter, underlying_type
    except Exception:
        # If reflection fails, skip this field
        pass

    return None


@functools.lru_cache(maxsize=None)
def _cached_serialization_map(target_class: type) -> Dict[str, Tuple[str, Optional[type], Any]]:
    """
    Cache and return a mapping of Python field names to serialization metadata.

    Maps: Python field name -> (DB alias, converter class, underlying type)

    This is cached with lru_cache since class schemas are immutable at runtime,
    eliminating reflection overhead for repeated serialization operations.

    Args:
        target_class: The model class to inspect

    Returns:
        Dict mapping field_name -> (db_alias, converter_class, core_type)
    """
    metadata_registry = {}

    for f in dataclasses.fields(target_class):
        field_metadata = _parse_field_metadata(f)
        if field_metadata:
            db_alias, converter_class, core_type = field_metadata
            metadata_registry[f.name] = (db_alias, converter_class, core_type)

    return metadata_registry


@functools.lru_cache(maxsize=None)
def _cached_deserialization_map(target_class: type) -> Dict[str, Tuple[str, Optional[type], Any]]:
    """
    Cache and return a mapping of DynamoDB attribute names to deserialization metadata.

    Maps: DB attribute name -> (Python field name, converter class, underlying type)

    This is the inverse of _cached_serialization_map and is cached for the same reason.

    Args:
        target_class: The model class to inspect

    Returns:
        Dict mapping db_alias -> (field_name, converter_class, core_type)
    """
    metadata_registry = {}

    for f in dataclasses.fields(target_class):
        field_metadata = _parse_field_metadata(f)
        if field_metadata:
            db_alias, converter_class, core_type = field_metadata
            metadata_registry[db_alias] = (f.name, converter_class, core_type)

    return metadata_registry
