# field_organization/field_manager.py
"""Unified field management system for DICOM metadata."""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Import settings management
from settings import get_settings_manager


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
        # Complete field definitions (unfiltered)
        self._complete_field_definitions: List[FieldDefinition] = []
        # Filtered field definitions (for actual use)
        self._filtered_field_definitions: List[FieldDefinition] = []
        
        self.translations: Dict[str, str] = {}
        self._category_fields: Dict[str, List[str]] = defaultdict(list)
        self._filter_initialized = False
        
        # Load initial data
        self._load_field_definitions()
        self._update_language()  # Get language from settings
        self._sort_fields()
        self._build_category_map()
        
        # Don't update filtered definitions yet - wait for settings initialization
        
        # Initialize settings filter configuration with complete field structure
        settings_manager = get_settings_manager()
        complete_structure = self.get_complete_field_structure()
        settings_manager.initialize_filter_settings(complete_structure)
        
        # Now update filtered definitions
        self._update_filtered_definitions()
        self._filter_initialized = True
    
    def _load_field_definitions(self):
        """Load field definitions from JSON."""
        json_path = Path(__file__).parent / "field_metadata.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._complete_field_definitions.clear()
        
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
            self._complete_field_definitions.append(field_def)
    
    def _update_language(self):
        """Update language from settings manager."""
        settings_manager = get_settings_manager()
        self.current_language = settings_manager.language
        self._load_translations()
    
    def _load_translations(self):
        """Load translations for current language."""
        lang_file = Path(__file__).parent.parent / "languages" / f"{self.current_language}.json"
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            print(f"Language file not found: {lang_file}")
            self.translations = {}
        
        # Apply translations to complete field definitions
        for field_def in self._complete_field_definitions:
            field_def.translated_name = self.translations.get(field_def.index, field_def.index)
        
        # Update filtered definitions with new translations
        self._update_filtered_definitions()
    
    def _sort_fields(self):
        """Sort complete field definitions by category, priority, and index."""
        def sort_key(field_def: FieldDefinition) -> Tuple[int, int, str]:
            try:
                category_index = CATEGORY_ORDER.index(field_def.category)
            except ValueError:
                category_index = len(CATEGORY_ORDER)
            return (category_index, field_def.priority, field_def.index)
        
        self._complete_field_definitions.sort(key=sort_key)
    
    def _build_category_map(self):
        """Build mapping of categories to field indices from complete definitions."""
        self._category_fields.clear()
        for field_def in self._complete_field_definitions:
            self._category_fields[field_def.category].append(field_def.index)
    
    def _update_filtered_definitions(self):
        """Update filtered field definitions based on current filter settings."""
        settings_manager = get_settings_manager()
        
        # Clear and rebuild filtered definitions
        self._filtered_field_definitions = []
        
        for field_def in self._complete_field_definitions:
            # Check if field should be visible
            if settings_manager.is_field_visible(field_def.index):
                # Create a copy of the field definition
                filtered_def = FieldDefinition(
                    index=field_def.index,
                    tag=field_def.tag,
                    category=field_def.category,
                    priority=field_def.priority,
                    interpret_mode=field_def.interpret_mode,
                    translated_name=field_def.translated_name
                )
                self._filtered_field_definitions.append(filtered_def)
    
    def check_and_update_filters(self):
        """Check if filter settings have changed and update if necessary."""
        settings_manager = get_settings_manager()
        
        # Don't check if not initialized
        if not hasattr(self, '_previous_filter_settings'):
            self._previous_filter_settings = {}
        
        current_filter_settings = settings_manager.filter_settings.to_dict()
        
        if current_filter_settings != self._previous_filter_settings:
            self._previous_filter_settings = current_filter_settings
            self._update_filtered_definitions()
            return True
        return False
    
    def set_language(self, language: str):
        """Change language and reload translations."""
        # Language is now managed by settings
        settings_manager = get_settings_manager()
        settings_manager.language = language
        self._update_language()
    
    def get_field_structure(self) -> List[Dict[str, Any]]:
        """Get sorted FILTERED field structure with translations."""
        # Update language in case it changed
        settings_manager = get_settings_manager()
        if settings_manager.language != self.current_language:
            self._update_language()
        
        # Only check for filter updates if filter is initialized
        if self._filter_initialized:
            self.check_and_update_filters()
        
        return [
            {
                "name": field_def.translated_name,
                "index": field_def.index,
                "tag": field_def.tag,
                "category": field_def.category,
                "priority": field_def.priority,
                "interpret_mode": field_def.interpret_mode
            }
            for field_def in self._filtered_field_definitions
        ]
    
    def get_complete_field_structure(self) -> List[Dict[str, Any]]:
        """Get sorted COMPLETE field structure with translations (for settings UI)."""
        # Update language in case it changed
        self._update_language()
        
        return [
            {
                "name": field_def.translated_name,
                "index": field_def.index,
                "tag": field_def.tag,
                "category": field_def.category,
                "priority": field_def.priority,
                "interpret_mode": field_def.interpret_mode
            }
            for field_def in self._complete_field_definitions
        ]
    
    def get_field_definitions(self) -> List[FieldDefinition]:
        """Get filtered field definitions."""
        # Only check for updates if filter is initialized
        if self._filter_initialized:
            self.check_and_update_filters()
        return self._filtered_field_definitions
    
    def get_categories_with_fields(self) -> Dict[str, Dict[str, Any]]:
        """Get COMPLETE categories with their field information (for settings UI)."""
        # Update language in case it changed
        self._update_language()
        
        result = {}
        for category in CATEGORY_ORDER:
            if category in self._category_fields:
                fields = []
                for field_index in self._category_fields[category]:
                    # Find field definition in complete list
                    for field_def in self._complete_field_definitions:
                        if field_def.index == field_index:
                            fields.append({
                                "index": field_index,
                                "name": field_def.translated_name
                            })
                            break
                
                # Translate category name
                category_key = f"CATEGORY_{category}"
                category_name = self.translations.get(category_key, category)
                result[category] = {
                    "name": category_name,
                    "fields": fields
                }
        
        return result
    
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
    
    def notify_filter_update(self):
        """Notify that filter settings have been updated."""
        self._update_filtered_definitions()


# Global instance
_field_manager: Optional[FieldManager] = None


def get_field_manager() -> FieldManager:
    """Get or create global FieldManager instance."""
    global _field_manager
    if _field_manager is None:
        _field_manager = FieldManager()
    return _field_manager