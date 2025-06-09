# field_organization/__init__.py
"""Field organization module for DICOM metadata display."""

from .field_manager import get_field_manager, FieldManager, FieldDefinition

__all__ = [
    "get_field_manager",
    "FieldManager", 
    "FieldDefinition",
]