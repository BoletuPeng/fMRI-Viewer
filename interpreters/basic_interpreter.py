# interpreters/basic_interpreter.py
"""Basic field interpreter for simple DICOM metadata fields."""
from typing import Dict, Any, Optional


def interpret_basic_fields(raw_meta: Dict[str, Any]) -> Dict[str, str]:
    """
    解读基础DICOM字段，处理简单的字符串转换和格式化
    
    参数:
        raw_meta: 原始元数据字典
        
    返回:
        Dict[str, str]: 解读后的字段字典
    """
    interpreted = {}
    
    # 文件信息
    interpreted["File Name"] = raw_meta.get("file_name", "–")
    interpreted["Transfer Syntax UID"] = _safe_str(raw_meta.get("transfer_syntax_uid"))
    
    # 患者信息
    interpreted["Patient Name"] = _safe_str(raw_meta.get("patient_name"))
    interpreted["Patient ID"] = _safe_str(raw_meta.get("patient_id"))
    interpreted["Sex"] = _interpret_sex(raw_meta.get("sex"))
    interpreted["Age"] = _interpret_age(raw_meta.get("age"))
    
    # 设备信息
    interpreted["Institution"] = _safe_str(raw_meta.get("institution"))
    interpreted["Station Name"] = _safe_str(raw_meta.get("station_name"))
    interpreted["Manufacturer"] = _safe_str(raw_meta.get("manufacturer"))
    interpreted["Device Model"] = _safe_str(raw_meta.get("device_model"))
    interpreted["Magnetic Field Strength"] = _interpret_magnetic_field(raw_meta.get("magnetic_field"))
    
    # 检查信息
    interpreted["Modality"] = _safe_str(raw_meta.get("modality"))
    interpreted["Study Date"] = _interpret_date(raw_meta.get("study_date"))
    interpreted["Study Time"] = _interpret_time(raw_meta.get("study_time"))
    interpreted["Series Description"] = _safe_str(raw_meta.get("series_description"))
    interpreted["Protocol Name"] = _safe_str(raw_meta.get("protocol_name"))
    
    # 扫描参数
    interpreted["Scanning Sequence"] = _safe_str(raw_meta.get("scanning_sequence"))
    interpreted["Sequence Variant"] = _safe_str(raw_meta.get("sequence_variant"))
    interpreted["TR (ms)"] = _interpret_numeric(raw_meta.get("tr"), unit="")
    interpreted["TE (ms)"] = _interpret_numeric(raw_meta.get("te"), unit="")
    interpreted["TI (ms)"] = _interpret_numeric(raw_meta.get("ti"), unit="")
    interpreted["Flip Angle (°)"] = _interpret_numeric(raw_meta.get("flip_angle"), unit="")
    interpreted["Echo Train Length"] = _interpret_numeric(raw_meta.get("echo_train_length"), unit="")
    interpreted["Number of Averages"] = _interpret_numeric(raw_meta.get("number_of_averages"), unit="")
    interpreted["Pixel Bandwidth"] = _interpret_numeric(raw_meta.get("pixel_bandwidth"), unit="")
    
    # 图像空间信息
    interpreted["Rows × Columns"] = _interpret_image_dimensions(raw_meta.get("rows"), raw_meta.get("columns"))
    interpreted["Slice Thickness"] = _interpret_numeric(raw_meta.get("slice_thickness"), unit=" mm")
    interpreted["Slice Spacing"] = _interpret_numeric(raw_meta.get("slice_spacing"), unit=" mm")
    interpreted["Pixel Spacing"] = _interpret_pixel_spacing(raw_meta.get("pixel_spacing"))
    interpreted["Acquisition Matrix"] = _interpret_matrix(raw_meta.get("acquisition_matrix"))
    interpreted["Bits Stored"] = _interpret_numeric(raw_meta.get("bits_stored"), unit="")
    interpreted["Photometric Interpretation"] = _safe_str(raw_meta.get("photometric_interpretation"))
    
    return interpreted


def _safe_str(value: Any, default: str = "–") -> str:
    """安全转换为字符串"""
    if value is None:
        return default
    return str(value).strip() if str(value).strip() else default


def _interpret_numeric(value: Any, unit: str = "", decimals: int = 1) -> str:
    """解读数值字段"""
    if value is None:
        return "–"
    try:
        num = float(value)
        if decimals == 0:
            return f"{int(num)}{unit}"
        else:
            return f"{num:.{decimals}f}{unit}"
    except (ValueError, TypeError):
        return "–"


def _interpret_sex(value: Any) -> str:
    """解读性别字段"""
    if value is None:
        return "–"
    sex_map = {
        "M": "Male",
        "F": "Female",
        "O": "Other"
    }
    return sex_map.get(str(value).upper(), str(value))


def _interpret_age(value: Any) -> str:
    """解读年龄字段"""
    if value is None:
        return "–"
    age_str = str(value)
    if len(age_str) >= 4:
        num = age_str[:-1]
        unit = age_str[-1].upper()
        unit_map = {"Y": "years", "M": "months", "W": "weeks", "D": "days"}
        if unit in unit_map:
            return f"{num} {unit_map[unit]}"
    return age_str


def _interpret_date(value: Any) -> str:
    """解读日期字段 (YYYYMMDD -> YYYY-MM-DD)"""
    if value is None:
        return "–"
    date_str = str(value)
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def _interpret_time(value: Any) -> str:
    """解读时间字段 (HHMMSS.FFF -> HH:MM:SS)"""
    if value is None:
        return "–"
    time_str = str(value).split(".")[0]  # 移除毫秒
    if len(time_str) >= 6 and time_str[:6].isdigit():
        return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
    return str(value)


def _interpret_magnetic_field(value: Any) -> str:
    """解读磁场强度"""
    if value is None:
        return "–"
    try:
        field = float(value)
        return f"{field:.1f} T"
    except (ValueError, TypeError):
        return "–"


def _interpret_image_dimensions(rows: Any, columns: Any) -> str:
    """解读图像尺寸"""
    if rows is not None and columns is not None:
        return f"{rows} × {columns}"
    return "–"


def _interpret_pixel_spacing(value: Any) -> str:
    """解读像素间距"""
    if value is None:
        return "–"
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return f"{float(value[0]):.2f} × {float(value[1]):.2f} mm"
        else:
            return str(value)
    except (ValueError, TypeError, IndexError):
        return "–"


def _interpret_matrix(value: Any) -> str:
    """解读采集矩阵"""
    if value is None:
        return "–"
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 4:
            # 通常格式为 [freq_rows, freq_cols, phase_rows, phase_cols]
            return f"{value[0]}×{value[1]} / {value[2]}×{value[3]}"
        else:
            return str(value)
    except (TypeError, IndexError):
        return str(value) if value else "–"