# field_organization/field_manager.py
"""Unified field management system for DICOM metadata."""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


# Category display order
CATEGORY_ORDER = [
    "FILE_INFO",
    "PATIENT_INFO",
    "INSTITUTION_EQUIPMENT",
    "STUDY_INFO",
    "SEQUENCE_INFO",
    "ACQUISITION_PARAMS",
    "IMAGE_GEOMETRY",
    "IMAGE_ENCODING",
    "SLICE_TIMING"
]


@dataclass
class FieldDefinition:
    """Definition of a DICOM field."""
    index: str
    tag: Any  # Can be tuple, list, string, or special value
    category: str
    priority: int
    interpret_mode: str
    translated_name: str = ""  # Will be filled by translator


class FieldManager:
    """Manages DICOM field definitions, translations, and ordering."""
    
    def __init__(self):
        self.field_definitions: List[FieldDefinition] = []
        self.current_language = "english"
        self.translations: Dict[str, str] = {}
        self._load_field_definitions()
        self._load_translations()
        self._sort_fields()
    
    def _load_field_definitions(self):
        """Load field definitions from JSON."""
        json_path = Path(__file__).parent / "field_metadata.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for field_data in data["fields"]:
            # Convert tag representation
            tag = field_data["tag"]
            if isinstance(tag, list) and len(tag) == 2 and isinstance(tag[0], int):
                # Convert decimal to hex tuple: [8, 128] -> (0x0008, 0x0080)
                tag = (tag[0], tag[1])
            
            field_def = FieldDefinition(
                index=field_data["index"],
                tag=tag,
                category=field_data["category"],
                priority=field_data["priority"],
                interpret_mode=field_data["interpret_mode"]
            )
            self.field_definitions.append(field_def)
    
    def _load_translations(self):
        """Load translations for current language."""
        lang_file = Path(__file__).parent.parent / "languages" / f"{self.current_language}.json"
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            print(f"Language file not found: {lang_file}")
            self.translations = {}
        
        # Apply translations to field definitions
        for field_def in self.field_definitions:
            field_def.translated_name = self.translations.get(field_def.index, field_def.index)
    
    def _sort_fields(self):
        """Sort fields by category, priority, and index."""
        def sort_key(field_def: FieldDefinition) -> Tuple[int, int, str]:
            try:
                category_index = CATEGORY_ORDER.index(field_def.category)
            except ValueError:
                category_index = len(CATEGORY_ORDER)
            return (category_index, field_def.priority, field_def.index)
        
        self.field_definitions.sort(key=sort_key)
    
    def set_language(self, language: str):
        """Change language and reload translations."""
        self.current_language = language
        self._load_translations()
    
    def get_field_structure(self) -> List[Dict[str, Any]]:
        """Get sorted field structure with translations."""
        return [
            {
                "name": field_def.translated_name,
                "index": field_def.index,
                "tag": field_def.tag,
                "category": field_def.category,
                "priority": field_def.priority,
                "interpret_mode": field_def.interpret_mode
            }
            for field_def in self.field_definitions
        ]
    
    def get_field_definitions(self) -> List[FieldDefinition]:
        """Get raw field definitions."""
        return self.field_definitions
    
    def translate_value(self, value: str) -> str:
        """Translate value components (VALUE_*, MSG_*)."""
        if isinstance(value, str):
            parts = value.split()
            translated_parts = []
            
            for part in parts:
                if part.startswith(('VALUE_', 'MSG_')):
                    translated_part = self.translations.get(part, part)
                    translated_parts.append(translated_part)
                else:
                    translated_parts.append(part)
            
            return ' '.join(translated_parts)
        
        return str(value)


# Global instance
_field_manager: Optional[FieldManager] = None


def get_field_manager() -> FieldManager:
    """Get or create global FieldManager instance."""
    global _field_manager
    if _field_manager is None:
        _field_manager = FieldManager()
    return _field_manager