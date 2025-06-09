# interpreters/specific_interpreters.py
"""Specific interpreters for DICOM fields that need special handling."""
from typing import Any, Dict, Optional, List, Tuple
import numpy as np
from .slice_timing_interpreter import interpret_slice_timing
import pydicom

def META_SEX(value: Any) -> str:
    """Interpret sex field."""
    if value is None:
        return "–"
    sex_map = {
        "M": "VALUE_MALE",
        "F": "VALUE_FEMALE",
        "O": "VALUE_OTHER"
    }
    return sex_map.get(str(value).upper(), str(value))


def META_AGE(value: Any) -> str:
    """Interpret age field."""
    if value is None:
        return "–"
    age_str = str(value)
    if len(age_str) >= 4:
        num = age_str[:-1]
        unit = age_str[-1].upper()
        unit_map = {
            "Y": "VALUE_YEARS",
            "M": "VALUE_MONTHS",
            "W": "VALUE_WEEKS",
            "D": "VALUE_DAYS"
        }
        if unit in unit_map:
            return f"{num} {unit_map[unit]}"
    return age_str


def META_MAGNETIC_FIELD_STRENGTH(value: Any) -> str:
    """Interpret magnetic field strength."""
    if value is None:
        return "–"
    try:
        field = float(value)
        return f"{field:.1f} T"
    except (ValueError, TypeError):
        return "–"


def META_STUDY_DATE(value: Any) -> str:
    """Interpret date field (YYYYMMDD -> YYYY-MM-DD)."""
    if value is None:
        return "–"
    date_str = str(value)
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def META_STUDY_TIME(value: Any) -> str:
    """Interpret time field (HHMMSS.FFF -> HH:MM:SS)."""
    if value is None:
        return "–"
    time_str = str(value).split(".")[0]  # Remove milliseconds
    if len(time_str) >= 6 and time_str[:6].isdigit():
        return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
    return str(value)


def META_TR_MS(value: Any) -> str:
    """Interpret TR value."""
    return _interpret_numeric(value, decimals=1)


def META_TE_MS(value: Any) -> str:
    """Interpret TE value."""
    return _interpret_numeric(value, decimals=1)


def META_TI_MS(value: Any) -> str:
    """Interpret TI value."""
    return _interpret_numeric(value, decimals=1)


def META_FLIP_ANGLE(value: Any) -> str:
    """Interpret flip angle."""
    return _interpret_numeric(value, decimals=1)


def META_ECHO_TRAIN_LENGTH(value: Any) -> str:
    """Interpret echo train length."""
    return _interpret_numeric(value, decimals=0)


def META_NUMBER_OF_AVERAGES(value: Any) -> str:
    """Interpret number of averages."""
    return _interpret_numeric(value, decimals=1)


def META_PIXEL_BANDWIDTH(value: Any) -> str:
    """Interpret pixel bandwidth."""
    return _interpret_numeric(value, decimals=1)


def META_ROWS_COLUMNS(value: Tuple[Any, Any]) -> str:
    """Interpret image dimensions from (rows, columns) tuple."""
    if isinstance(value, tuple) and len(value) == 2:
        rows, columns = value
        if rows is not None and columns is not None:
            return f"{rows} × {columns}"
    return "–"


def META_SLICE_THICKNESS(value: Any) -> str:
    """Interpret slice thickness."""
    result = _interpret_numeric(value, decimals=2)
    if result != "–":
        return f"{result} mm"
    return result


def META_SLICE_SPACING(value: Any) -> str:
    """Interpret slice spacing."""
    result = _interpret_numeric(value, decimals=2)
    if result != "–":
        return f"{result} mm"
    return result


def META_PIXEL_SPACING(value: Any) -> str:
    """Interpret pixel spacing."""
    if value is None:
        return "–"
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return f"{float(value[0]):.2f} × {float(value[1]):.2f} mm"
        else:
            return str(value)
    except (ValueError, TypeError, IndexError):
        return "–"


def META_ACQUISITION_MATRIX(value: Any) -> str:
    """Interpret acquisition matrix."""
    if value is None:
        return "–"
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 4:
            # Format: [freq_rows, freq_cols, phase_rows, phase_cols]
            return f"{value[0]}×{value[1]} / {value[2]}×{value[3]}"
        else:
            return str(value)
    except (TypeError, IndexError):
        return str(value) if value else "–"


def META_BITS_STORED(value: Any) -> str:
    """Interpret bits stored."""
    return _interpret_numeric(value, decimals=0)


def META_SLICE_TIMING(value: Dict[str, Any]) -> Dict[str, str]:
    """
    Interpret slice timing context.
    Returns a dictionary of interpreted timing fields.
    """
    if not isinstance(value, dict):
        return {"META_SLICE_TIMING_AVAILABLE": "VALUE_NO"}
    
    # Call the existing slice timing interpreter
    result = interpret_slice_timing(value)
    
    # Flatten the result if needed
    if isinstance(result, dict):
        return result
    else:
        return {"META_SLICE_TIMING_ERROR": "MSG_FAILED_TO_PARSE"}

def META_TRANSFER_SYNTAX_UID(value: Any) -> str:
    """seen https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_a.html"""
    """Interpret Transfer Syntax UID to human-readable format."""
    if value is None:
        return "–"
    try:
        # Convert to UID object if it's a string
        uid = pydicom.uid.UID(str(value))

        # Get the human-readable name
        name = uid.name
        return f"{name}"
            
    except Exception:
        # If any error occurs, just return the raw value
        return str(value)


# Helper function
def _interpret_numeric(value: Any, decimals: int = 1) -> str:
    """Interpret numeric value with specified decimal places."""
    if value is None:
        return "–"
    try:
        num = float(value)
        if decimals == 0:
            return str(int(num))
        else:
            return f"{num:.{decimals}f}"
    except (ValueError, TypeError):
        return "–"
    


