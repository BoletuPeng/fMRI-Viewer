# dicom_utils.py
"""DICOM controller with unified field management system."""
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pydicom
from pydicom.dataset import FileDataset

# Import field management
from field_organization import get_field_manager

# Import specific interpreters
from interpreters import specific_interpreters

__all__ = ["DicomController", "load_dicom_images", "load_dicom_full"]


class DicomController:
    """DICOM file controller with unified metadata handling."""
    
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._ds: Optional[FileDataset] = None
        self._images: Optional[List[np.ndarray]] = None
        self._metadata: Optional[List[Dict[str, Any]]] = None
    
    @property
    def dataset(self) -> FileDataset:
        """Lazy load DICOM dataset."""
        if self._ds is None:
            self._ds = pydicom.dcmread(str(self.path))
        return self._ds
    
    def _extract_images(self) -> List[np.ndarray]:
        """Extract image frames."""
        if self._images is None:
            try:
                pixel = self.dataset.pixel_array
                if pixel.ndim == 2:
                    self._images = [pixel]
                elif pixel.ndim == 3:
                    self._images = [pixel[i] for i in range(pixel.shape[0])]
                else:
                    self._images = [pixel]
            except Exception:
                self._images = []
        return self._images
    
    def _safe_get(self, tag_spec: Any) -> Any:
        """
        Safely get value from dataset based on tag specification.
        
        Args:
            tag_spec: Can be:
                - Tuple of ints: (group, element) for standard DICOM tag
                - String: Direct attribute name
                - List: Special handling for complex tags
        """
        ds = self.dataset
        
        if isinstance(tag_spec, tuple) and len(tag_spec) == 2:
            # Standard DICOM tag
            elem = ds.get(tag_spec)
            return elem.value if elem is not None else None
            
        elif isinstance(tag_spec, str):
            # Direct attribute or special value
            if tag_spec == "file_name":
                return self.path.name
            elif tag_spec == "slice_timing_context":
                # Build context for slice timing interpreter
                return self._build_slice_timing_context()
            else:
                # Try to get as attribute
                return getattr(ds, tag_spec, None)
                
        elif isinstance(tag_spec, list):
            # Special handling for complex tags
            if tag_spec == ["file_meta", "TransferSyntaxUID"]:
                return str(ds.file_meta.TransferSyntaxUID) if hasattr(ds, 'file_meta') else None
            elif tag_spec == ["Rows", "Columns"]:
                rows = getattr(ds, 'Rows', None)
                columns = getattr(ds, 'Columns', None)
                return (rows, columns) if rows and columns else None
                
        return None
    
    def _build_slice_timing_context(self) -> Dict[str, Any]:
        """Build context for slice timing interpretation."""
        ds = self.dataset
        
        def safe_get_tag(tag_tuple):
            elem = ds.get(tag_tuple)
            return elem.value if elem is not None else None
        
        # Check if this is an EPI sequence
        scanning_seq = str(safe_get_tag((0x0018, 0x0020)) or "").upper()
        if "EP" not in scanning_seq:
            return {}
        
        return {
            "manufacturer": safe_get_tag((0x0008, 0x0070)),
            "device_model": safe_get_tag((0x0008, 0x1090)),
            "scanning_sequence": scanning_seq,
            "image_type": safe_get_tag((0x0008, 0x0008)),
            "tr": safe_get_tag((0x0018, 0x0080)),
            "rows": getattr(ds, 'Rows', None),
            "columns": getattr(ds, 'Columns', None),
            # Timing tags
            "slice_timing_siemens": safe_get_tag((0x0019, 0x1029)),
            "trigger_time": safe_get_tag((0x0018, 0x1060)),
            "rtia_timer": safe_get_tag((0x0021, 0x105E)),
            "protocol_data_block": safe_get_tag((0x0025, 0x101B)),
            "temporal_position_identifier": safe_get_tag((0x0020, 0x0100)),
            "frame_acquisition_time": safe_get_tag((0x0018, 0x9074)),
        }
    
    def _extract_metadata(self) -> List[Dict[str, Any]]:
        """Extract and interpret metadata based on filtered field structure."""
        if self._metadata is None:
            field_manager = get_field_manager()
            # Get filtered field structure
            field_structure = field_manager.get_field_structure()
            
            metadata = []
            
            for field_info in field_structure:
                # Get raw value
                raw_value = self._safe_get(field_info["tag"])
                
                # Interpret value if needed
                if field_info["interpret_mode"] == "Specific":
                    # Get interpreter function by index name
                    interpreter_func = getattr(specific_interpreters, field_info["index"], None)
                    if interpreter_func:
                        interpreted_value = interpreter_func(raw_value)
                        
                        # Handle slice timing special case (returns dict)
                        if field_info["index"] == "META_SLICE_TIMING" and isinstance(interpreted_value, dict):
                            # Add each timing field to metadata
                            for key, value in interpreted_value.items():
                                timing_field = {
                                    "name": field_manager.translations.get(key, key),
                                    "value": field_manager.translate_value(value)
                                }
                                metadata.append(timing_field)
                            continue
                        else:
                            raw_value = interpreted_value
                
                # Convert None to display string
                if raw_value is None:
                    raw_value = "–"
                
                # Translate value components
                final_value = field_manager.translate_value(str(raw_value))
                
                # Add to metadata
                metadata.append({
                    "name": field_info["name"],
                    "value": final_value
                })
            
            self._metadata = metadata
        
        return self._metadata
    
    def get_images(self) -> List[np.ndarray]:
        """Get only images (no metadata)."""
        return self._extract_images()
    
    def get_metadata(self) -> List[Dict[str, str]]:
        """Get only metadata as ordered list."""
        # Clear cache to ensure fresh data
        self._metadata = None
        return self._extract_metadata()
    
    def get_full_data(self) -> Tuple[List[Dict[str, str]], List[np.ndarray]]:
        """Get both metadata and images."""
        # Clear cache to ensure fresh data with current language/filters
        self._metadata = None
        
        metadata = self._extract_metadata()
        images = self._extract_images()
        return metadata, images


# Convenience functions for backward compatibility
def load_dicom_images(path: str | Path) -> List[np.ndarray]:
    """Load only DICOM images."""
    controller = DicomController(path)
    return controller.get_images()


def load_dicom_full(path: str | Path) -> Tuple[List[Dict[str, str]], List[np.ndarray]]:
    """Load full DICOM data (metadata + images)."""
    controller = DicomController(path)
    return controller.get_full_data()


# Backward compatibility alias
load_dicom = load_dicom_full