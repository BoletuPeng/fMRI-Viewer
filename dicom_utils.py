"""Helper for loading a DICOM file and returning (metadata, images)."""
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pydicom
from pydicom.dataset import FileDataset

__all__ = ["load_dicom"]


def _to_numpy_frames(ds: FileDataset) -> List[np.ndarray]:
    """Return a list of frames as numpy arrays (grayscale 2-D)."""
    pixel = ds.pixel_array                                   # pydicom 负责解压
    if pixel.ndim == 2:                                      # 单帧
        return [pixel]
    if pixel.ndim == 3:                                      # 多帧 (f, h, w)
        return [pixel[i] for i in range(pixel.shape[0])]
    return [pixel]                                           # 其它维度，尽量返回原数据


def load_dicom(path: str | Path) -> Tuple[Dict[str, str], List[np.ndarray]]:
    """Read *path* and return (metadata dict, list of image frames)."""
    path = Path(path)
    ds: FileDataset = pydicom.dcmread(str(path))

    # 小工具：安全读取 Tag，缺失返回 “–”
    def tag(tag_tuple, default: str = "–") -> str:
        elem = ds.get(tag_tuple)
        return str(elem.value) if elem is not None else default

    meta: Dict[str, str] = {
        # —— 文件级别 —— #
        "File Name":              path.name,
        "Transfer Syntax UID":    str(ds.file_meta.TransferSyntaxUID),

        # —— 患者/受检者 —— #
        "Patient Name":           tag((0x0010, 0x0010)),
        "Patient ID":             tag((0x0010, 0x0020)),
        "Sex":                    tag((0x0010, 0x0040)),          # M / F / O
        "Age":                    tag((0x0010, 0x1010)),

        # —— 机构与设备 —— #
        "Institution":            tag((0x0008, 0x0080)),          # Institution Name
        "Station Name":           tag((0x0008, 0x1010)),
        "Manufacturer":           tag((0x0008, 0x0070)),
        "Device Model":           tag((0x0008, 0x1090)),
        "Magnetic Field Strength": tag((0x0018, 0x0087)),         # MR only, in Tesla

        # —— 检查信息 —— #
        "Modality":               tag((0x0008, 0x0060)),
        "Study Date":             tag((0x0008, 0x0020)),
        "Study Time":             tag((0x0008, 0x0030)),
        "Series Description":     tag((0x0008, 0x103E)),
        "Protocol Name":          tag((0x0018, 0x1030)),

        # —— 扫描序列及参数 —— #
        "Scanning Sequence":      tag((0x0018, 0x0020)),
        "Sequence Variant":       tag((0x0018, 0x0021)),
        "TR (ms)":                tag((0x0018, 0x0080)),
        "TE (ms)":                tag((0x0018, 0x0081)),
        "TI (ms)":                tag((0x0018, 0x0082)),
        "Flip Angle (°)":         tag((0x0018, 0x1314)),
        "Echo Train Length":      tag((0x0018, 0x0091)),
        "Number of Averages":     tag((0x0018, 0x0083)),
        "Pixel Bandwidth":        tag((0x0018, 0x0095)),

        # —— 图像空间信息 —— #
        "Rows × Columns":         f"{getattr(ds, 'Rows', '–')} × {getattr(ds, 'Columns', '–')}",
        "Slice Thickness":        tag((0x0018, 0x0050)),
        "Slice Spacing":          tag((0x0018, 0x0088)),          # Spacing Between Slices
        "Pixel Spacing":          tag((0x0028, 0x0030)),          # in-plane spacing
        "Acquisition Matrix":     tag((0x0018, 0x1310)),
        "Bits Stored":            tag((0x0028, 0x0101)),
        "Photometric Interpretation": tag((0x0028, 0x0004)),
    }

    # 尝试提取像素帧；如果失败（比如缺像素数据或不支持的压缩），保持空列表
    try:
        images = _to_numpy_frames(ds)
    except Exception:
        images: List[np.ndarray] = []

    return meta, images
