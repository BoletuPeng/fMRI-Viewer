# dicom_utils.py
"""DICOM controller with modular field interpretation system."""
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pydicom
from pydicom.dataset import FileDataset

# 导入解读模块
from interpreters.basic_interpreter import interpret_basic_fields
from interpreters.slice_timing_interpreter import interpret_slice_timing

__all__ = ["DicomController", "load_dicom_images", "load_dicom_full"]


class DicomController:
    """DICOM文件控制器，支持懒加载和模块化字段解读"""
    
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._ds: Optional[FileDataset] = None
        self._images: Optional[List[np.ndarray]] = None
        self._raw_meta: Optional[Dict[str, Any]] = None
        self._interpreted_meta: Optional[Dict[str, str]] = None
    
    @property
    def dataset(self) -> FileDataset:
        """懒加载DICOM数据集"""
        if self._ds is None:
            self._ds = pydicom.dcmread(str(self.path))
        return self._ds
    
    def _extract_images(self) -> List[np.ndarray]:
        """提取图像帧"""
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
    
    def _extract_raw_metadata(self) -> Dict[str, Any]:
        """提取原始元数据（不进行解读）"""
        if self._raw_meta is None:
            ds = self.dataset
            
            def safe_get(tag_tuple, default=None):
                elem = ds.get(tag_tuple)
                return elem.value if elem is not None else default
            
            self._raw_meta = {
                # 文件信息
                "file_name": self.path.name,
                "transfer_syntax_uid": str(ds.file_meta.TransferSyntaxUID) if hasattr(ds, 'file_meta') else None,
                
                # 患者信息
                "patient_name": safe_get((0x0010, 0x0010)),
                "patient_id": safe_get((0x0010, 0x0020)),
                "sex": safe_get((0x0010, 0x0040)),
                "age": safe_get((0x0010, 0x1010)),
                
                # 设备信息
                "institution": safe_get((0x0008, 0x0080)),
                "station_name": safe_get((0x0008, 0x1010)),
                "manufacturer": safe_get((0x0008, 0x0070)),
                "device_model": safe_get((0x0008, 0x1090)),
                "magnetic_field": safe_get((0x0018, 0x0087)),
                
                # 检查信息
                "modality": safe_get((0x0008, 0x0060)),
                "study_date": safe_get((0x0008, 0x0020)),
                "study_time": safe_get((0x0008, 0x0030)),
                "series_description": safe_get((0x0008, 0x103E)),
                "protocol_name": safe_get((0x0018, 0x1030)),
                
                # 扫描参数
                "scanning_sequence": safe_get((0x0018, 0x0020)),
                "sequence_variant": safe_get((0x0018, 0x0021)),
                "tr": safe_get((0x0018, 0x0080)),
                "te": safe_get((0x0018, 0x0081)),
                "ti": safe_get((0x0018, 0x0082)),
                "flip_angle": safe_get((0x0018, 0x1314)),
                "echo_train_length": safe_get((0x0018, 0x0091)),
                "number_of_averages": safe_get((0x0018, 0x0083)),
                "pixel_bandwidth": safe_get((0x0018, 0x0095)),
                
                # 图像空间信息
                "rows": getattr(ds, 'Rows', None),
                "columns": getattr(ds, 'Columns', None),
                "slice_thickness": safe_get((0x0018, 0x0050)),
                "slice_spacing": safe_get((0x0018, 0x0088)),
                "pixel_spacing": safe_get((0x0028, 0x0030)),
                "acquisition_matrix": safe_get((0x0018, 0x1310)),
                "bits_stored": safe_get((0x0028, 0x0101)),
                "photometric_interpretation": safe_get((0x0028, 0x0004)),
                
                # Slice timing相关标签（不同厂商）
                # Siemens
                "slice_timing_siemens": safe_get((0x0019, 0x1029)),  # MosaicRefAcqTimes
                # GE
                "trigger_time": safe_get((0x0018, 0x1060)),  # Trigger Time
                "rtia_timer": safe_get((0x0021, 0x105E)),  # RTIA Timer (GE private)
                "protocol_data_block": safe_get((0x0025, 0x101B)),  # Protocol Data Block (GE)
                # 通用
                "temporal_position_identifier": safe_get((0x0020, 0x0100)),
                "frame_acquisition_time": safe_get((0x0018, 0x9074)),
                
                # 序列类型相关
                "image_type": safe_get((0x0008, 0x0008)),  # 用于判断是否为EPI/MOSAIC
                "series_plane": safe_get((0x0019, 0x1017)),  # GE specific
                "in_plane_phase_encoding_direction": safe_get((0x0018, 0x1312)),  # COL or ROW
                
                # 保留原始dataset引用，供复杂解读器使用
                "_dataset": ds
            }
        return self._raw_meta
    
    def _interpret_metadata(self) -> Dict[str, str]:
        """解读元数据，调用各个解读模块"""
        if self._interpreted_meta is None:
            raw = self._extract_raw_metadata()
            
            # 初始化解读结果字典
            interpreted = {}
            
            # 调用基础字段解读器
            basic_fields = interpret_basic_fields(raw)
            interpreted.update(basic_fields)
            
            # 判断是否需要调用slice timing解读器
            if self._should_interpret_slice_timing(raw):
                # 准备slice timing解读所需的关键字段
                timing_context = {
                    "manufacturer": raw.get("manufacturer"),
                    "device_model": raw.get("device_model"),
                    "scanning_sequence": raw.get("scanning_sequence"),
                    "image_type": raw.get("image_type"),
                    "tr": raw.get("tr"),
                    "rows": raw.get("rows"),
                    "columns": raw.get("columns"),
                    # 所有可能的timing信息
                    "slice_timing_siemens": raw.get("slice_timing_siemens"),
                    "trigger_time": raw.get("trigger_time"),
                    "rtia_timer": raw.get("rtia_timer"),
                    "protocol_data_block": raw.get("protocol_data_block"),
                    "temporal_position_identifier": raw.get("temporal_position_identifier"),
                    "frame_acquisition_time": raw.get("frame_acquisition_time"),
                }
                
                slice_timing_results = interpret_slice_timing(timing_context)
                if slice_timing_results:
                    interpreted.update(slice_timing_results)
            
            # 这里可以继续添加其他专门的解读器
            # future_results = interpret_future_field(raw)
            # if future_results:
            #     interpreted.update(future_results)
            
            self._interpreted_meta = interpreted
        
        return self._interpreted_meta
    
    def _should_interpret_slice_timing(self, raw_meta: Dict[str, Any]) -> bool:
        """
        判断是否应该尝试解读slice timing信息
        
        基于以下条件：
        1. 序列类型是否为EPI相关（fMRI, DTI等）
        2. 是否存在相关的timing信息标签
        3. 厂商是否支持
        """
        # 检查扫描序列是否包含EP（Echo Planar）
        scanning_seq = str(raw_meta.get("scanning_sequence", "")).upper()
        if "EP" not in scanning_seq:
            return False
        
        # 检查image type是否包含EPI相关标记
        image_type = raw_meta.get("image_type")
        if image_type:
            image_type_str = str(image_type).upper()
            # 检查是否包含EPI, MOSAIC, FMRI等关键词
            epi_indicators = ["EPI", "MOSAIC", "FMRI", "DTI", "DWI", "BOLD"]
            if not any(indicator in image_type_str for indicator in epi_indicators):
                return False
        
        # 检查厂商
        manufacturer = str(raw_meta.get("manufacturer", "")).upper()
        supported_manufacturers = ["SIEMENS", "GE", "PHILIPS"]
        
        # 如果厂商不在支持列表中，返回False
        manufacturer_found = False
        for supported in supported_manufacturers:
            if supported in manufacturer:
                manufacturer_found = True
                break
        
        if not manufacturer_found:
            return False
        
        # 检查是否存在任何slice timing相关的标签
        timing_tags = [
            "slice_timing_siemens",
            "trigger_time",
            "rtia_timer",
            "protocol_data_block",
            "temporal_position_identifier",
            "frame_acquisition_time"
        ]
        
        for tag in timing_tags:
            if raw_meta.get(tag) is not None:
                return True
        
        return False
    
    def get_images(self) -> List[np.ndarray]:
        """仅获取图像（不触发元数据解读）"""
        return self._extract_images()
    
    def get_full_data(self) -> Tuple[Dict[str, str], List[np.ndarray]]:
        """获取完整数据（解读后的元数据 + 图像）"""
        meta = self._interpret_metadata()
        images = self._extract_images()
        return meta, images


# 便捷函数，保持向后兼容
def load_dicom_images(path: str | Path) -> List[np.ndarray]:
    """仅加载DICOM图像"""
    controller = DicomController(path)
    return controller.get_images()


def load_dicom_full(path: str | Path) -> Tuple[Dict[str, str], List[np.ndarray]]:
    """加载完整DICOM数据（解读后的元数据 + 图像）"""
    controller = DicomController(path)
    return controller.get_full_data()


# 保持向后兼容的别名
load_dicom = load_dicom_full