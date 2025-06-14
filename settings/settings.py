# settings/settings.py
"""Settings management module for persistent configuration."""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
import threading


@dataclass
class FilterSettings:
    """Filter settings for categories and fields."""
    categories: Dict[str, bool] = field(default_factory=dict)
    fields: Dict[str, bool] = field(default_factory=dict)
    
    def is_field_visible(self, field_index: str) -> bool:
        """Check if a field should be visible."""
        return self.fields.get(field_index, True)
    
    def is_category_visible(self, category: str) -> bool:
        """Check if a category should be visible."""
        return self.categories.get(category, True)
    
    def set_field_visibility(self, field_index: str, visible: bool):
        """Set field visibility."""
        self.fields[field_index] = visible
    
    def set_category_visibility(self, category: str, visible: bool):
        """Set category visibility."""
        self.categories[category] = visible
    
    def get_category_state(self, category: str, field_indices: List[str]) -> str:
        """
        Get category state based on its fields.
        Returns: 'checked', 'unchecked', or 'indeterminate'
        """
        if not field_indices:
            return 'checked'
        
        visible_count = sum(1 for idx in field_indices if self.is_field_visible(idx))
        
        if visible_count == 0:
            return 'unchecked'
        elif visible_count == len(field_indices):
            return 'checked'
        else:
            return 'indeterminate'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter settings to dictionary."""
        return {
            "categories": self.categories.copy(),
            "fields": self.fields.copy()
        }


@dataclass
class Settings:
    """Application settings."""
    language: str = "english"
    filter_settings: FilterSettings = field(default_factory=FilterSettings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "language": self.language,
            "filter_settings": {
                "categories": self.filter_settings.categories,
                "fields": self.filter_settings.fields
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        """Create from dictionary."""
        filter_data = data.get("filter_settings", {})
        filter_settings = FilterSettings(
            categories=filter_data.get("categories", {}),
            fields=filter_data.get("fields", {})
        )
        
        return cls(
            language=data.get("language", "english"),
            filter_settings=filter_settings
        )


class SettingsManager:
    """Manages application settings with persistence."""
    
    def __init__(self):
        self.settings_dir = Path(__file__).parent
        self.settings_file = self.settings_dir / "settings.json"
        self._settings: Settings = Settings()
        self._lock = threading.RLock()
        self._initialized = False
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from file (except filter settings)."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Only load language at this stage
                    self._settings.language = data.get("language", "english")
                    # Store filter data for later initialization
                    self._stored_filter_data = data.get("filter_settings", {})
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading settings: {e}")
                self._settings = Settings()
                self._stored_filter_data = {}
        else:
            self._stored_filter_data = {}
    
    def initialize_filter_settings(self, complete_field_structure: List[Dict[str, Any]]):
        """Initialize filter settings based on complete field structure."""
        with self._lock:
            if self._initialized:
                return
            
            # Get all field indices from complete structure
            all_field_indices = [field["index"] for field in complete_field_structure]
            
            # Initialize filter settings from stored data
            stored_fields = self._stored_filter_data.get("fields", {})
            stored_categories = self._stored_filter_data.get("categories", {})
            
            # Create new filter settings
            new_filter_settings = FilterSettings()
            
            # For each field, check if it has a stored setting
            for field_index in all_field_indices:
                if field_index in stored_fields:
                    new_filter_settings.fields[field_index] = stored_fields[field_index]
                else:
                    # Default to visible
                    new_filter_settings.fields[field_index] = True
            
            # Copy category settings
            new_filter_settings.categories = stored_categories.copy()
            
            # Update settings
            self._settings.filter_settings = new_filter_settings
            self._initialized = True
            
            # Save the initialized settings
            self._save_settings()
    
    def _save_settings(self):
        """Save settings to file."""
        with self._lock:
            # Ensure directory exists
            self.settings_dir.mkdir(exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings.to_dict(), f, indent=2, ensure_ascii=False)
    
    @property
    def language(self) -> str:
        """Get current language."""
        with self._lock:
            return self._settings.language
    
    @language.setter
    def language(self, value: str):
        """Set current language."""
        with self._lock:
            if self._settings.language != value:
                self._settings.language = value
                self._save_settings()
    
    @property
    def filter_settings(self) -> FilterSettings:
        """Get filter settings."""
        with self._lock:
            return self._settings.filter_settings
    
    def update_filter_settings(self, categories: Dict[str, bool], fields: Dict[str, bool]):
        """Update filter settings."""
        with self._lock:
            self._settings.filter_settings.categories = categories.copy()
            self._settings.filter_settings.fields = fields.copy()
            self._save_settings()
    
    def is_field_visible(self, field_index: str) -> bool:
        """Check if a field should be visible."""
        with self._lock:
            return self._settings.filter_settings.is_field_visible(field_index)
    
    def is_category_visible(self, category: str) -> bool:
        """Check if a category should be visible."""
        with self._lock:
            return self._settings.filter_settings.is_category_visible(category)
    
    def get_visible_field_indices(self, all_indices: List[str]) -> List[str]:
        """Get list of visible field indices."""
        with self._lock:
            return [idx for idx in all_indices if self.is_field_visible(idx)]
    
    def reset_filters(self):
        """Reset all filters to show everything."""
        with self._lock:
            self._settings.filter_settings = FilterSettings()
            self._save_settings()


# Global instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get or create global SettingsManager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager