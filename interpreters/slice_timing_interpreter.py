# interpreters/slice_timing_interpreter.py
"""Slice timing interpreter for multi-vendor DICOM files."""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np


def interpret_slice_timing(timing_context: Dict[str, Any]) -> Dict[str, str]:
    """
    解读多厂商slice timing信息
    
    参数:
        timing_context: 包含厂商、设备、序列类型和各种timing标签的上下文字典
        
    返回:
        Dict[str, str]: 解读结果字典，包含采集顺序和模式分析
    """
    manufacturer = str(timing_context.get("manufacturer", "")).upper()
    
    # 根据厂商选择解读策略
    if "SIEMENS" in manufacturer:
        return _interpret_siemens_timing(timing_context)
    elif "GE" in manufacturer:
        return _interpret_ge_timing(timing_context)
    elif "PHILIPS" in manufacturer:
        return _interpret_philips_timing(timing_context)
    else:
        return {"Slice Timing": "Unsupported manufacturer"}


def _interpret_siemens_timing(context: Dict[str, Any]) -> Dict[str, str]:
    """解读Siemens slice timing"""
    timing_info = context.get("slice_timing_siemens")  # (0019,1029)
    
    if timing_info is None:
        # 尝试备选方法
        frame_acq_time = context.get("frame_acquisition_time")
        if frame_acq_time:
            return {
                "Slice Timing Available": "Yes (Frame Acquisition Time)",
                "Slice Timing Source": "Public tag (0018,9074)",
                "Note": "Using frame acquisition time instead of MosaicRefAcqTimes"
            }
        return {"Slice Timing Available": "No", "Slice Timing Note": "Siemens timing tags not found"}
    
    try:
        # 提取采集顺序
        acquisition_order = _extract_acquisition_order(timing_info)
        
        if not acquisition_order:
            return {"Slice Timing Available": "Error", "Slice Timing Error": "Failed to parse timing data"}
        
        # 分析采集模式
        pattern_info = _analyze_acquisition_pattern(acquisition_order)
        
        # 获取额外的序列信息
        image_type = str(context.get("image_type", "")).upper()
        is_mosaic = "MOSAIC" in image_type
        
        # 构建返回结果
        results = {
            "Slice Timing Available": "Yes",
            "Slice Timing Source": "Siemens MosaicRefAcqTimes (0019,1029)",
            "Number of Slices": str(len(acquisition_order)),
            "Acquisition Order (first 8)": _format_order_preview(acquisition_order),
            "Acquisition Pattern": pattern_info["pattern_name"],
            "Image Type": "Mosaic" if is_mosaic else "Standard",
        }
        
        # 添加额外的模式信息
        if pattern_info.get("details"):
            results["Pattern Details"] = pattern_info["details"]
        
        # 如果有timing范围信息
        if "timing_range" in pattern_info:
            min_t, max_t = pattern_info["timing_range"]
            results["Timing Range (ms)"] = f"{min_t:.1f} - {max_t:.1f}"
            
            # 计算slice间隔（如果有TR信息）
            if context.get("tr"):
                try:
                    tr = float(context["tr"])
                    n_slices = len(acquisition_order)
                    estimated_slice_interval = tr / n_slices
                    results["Estimated Slice Interval (ms)"] = f"{estimated_slice_interval:.1f}"
                except:
                    pass
        
        return results
        
    except Exception as e:
        return {
            "Slice Timing Available": "Error",
            "Slice Timing Error": f"Siemens parsing error: {str(e)}"
        }


def _interpret_ge_timing(context: Dict[str, Any]) -> Dict[str, str]:
    """解读GE slice timing"""
    # 尝试多种方法获取timing信息
    trigger_time = context.get("trigger_time")  # (0018,1060)
    rtia_timer = context.get("rtia_timer")  # (0021,105E)
    protocol_block = context.get("protocol_data_block")  # (0025,101B)
    
    if trigger_time is not None:
        return {
            "Slice Timing Available": "Yes",
            "Slice Timing Source": "GE Trigger Time (0018,1060)",
            "Trigger Time": str(trigger_time),
            "Note": "Slice timing can be calculated from trigger times"
        }
    elif rtia_timer is not None:
        return {
            "Slice Timing Available": "Yes",
            "Slice Timing Source": "GE RTIA Timer (0021,105E)",
            "RTIA Timer": str(rtia_timer),
            "Note": "Using RTIA timer for slice timing"
        }
    elif protocol_block is not None:
        # Protocol block通常只包含采集顺序（顺序或交错），不包含精确时间
        return {
            "Slice Timing Available": "Partial",
            "Slice Timing Source": "GE Protocol Data Block (0025,101B)",
            "Note": "Only acquisition order available (sequential/interleaved), no precise timing",
            "Warning": "Timing estimation assumes continuous acquisition (TA ≈ TR)"
        }
    else:
        return {
            "Slice Timing Available": "No",
            "Slice Timing Note": "GE timing information not found in standard tags"
        }


def _interpret_philips_timing(context: Dict[str, Any]) -> Dict[str, str]:
    """解读Philips slice timing"""
    # Philips通常不在标准位置存储slice timing
    temporal_pos = context.get("temporal_position_identifier")
    frame_time = context.get("frame_acquisition_time")
    
    if temporal_pos is not None:
        return {
            "Slice Timing Available": "Partial",
            "Slice Timing Source": "Philips Temporal Position (0020,0100)",
            "Note": "Limited timing information available"
        }
    elif frame_time is not None:
        return {
            "Slice Timing Available": "Partial",
            "Slice Timing Source": "Frame Acquisition Time (0018,9074)",
            "Note": "Using frame acquisition time"
        }
    else:
        return {
            "Slice Timing Available": "No",
            "Slice Timing Note": "Philips typically does not store slice timing in DICOM headers",
            "Recommendation": "Check scanner console or protocol documentation"
        }


def _extract_acquisition_order(timing_info: Any) -> Optional[List[int]]:
    """
    从timing信息中提取采集顺序（通用函数）
    
    返回:
        List[int]: 1-based的slice采集顺序
    """
    try:
        # 转换为列表
        if isinstance(timing_info, (list, tuple)):
            timing_array = list(timing_info)
        elif isinstance(timing_info, np.ndarray):
            timing_array = timing_info.tolist()
        else:
            timing_array = [float(timing_info)]
        
        # 转换为浮点数
        timing_array = [float(t) for t in timing_array]
        
        # 创建 (timing, index) 对并排序
        timing_with_index = [(t, i + 1) for i, t in enumerate(timing_array)]
        sorted_by_timing = sorted(timing_with_index, key=lambda x: x[0])
        
        # 返回采集顺序
        order = [idx for _, idx in sorted_by_timing]
        
        # 同时保存timing范围供后续使用
        global _last_timing_range
        _last_timing_range = (min(timing_array), max(timing_array))
        
        return order
        
    except Exception:
        return None


def _analyze_acquisition_pattern(order: List[int]) -> Dict[str, Any]:
    """
    分析采集模式（增强版）
    
    返回:
        Dict包含:
        - pattern_name: 模式名称
        - details: 详细描述
        - timing_range: timing范围（如果可用）
        - is_multiband: 是否为多带采集
    """
    n = len(order)
    result = {"pattern_name": "Unknown"}
    
    # 添加timing范围（如果可用）
    global _last_timing_range
    if '_last_timing_range' in globals():
        result["timing_range"] = _last_timing_range
    
    # 检查是否为多带采集（同时采集的slice具有相同的timing）
    timing_counts = {}
    if '_last_timing_range' in globals():
        # 需要原始timing数组来检查多带
        result["is_multiband"] = False  # 暂时设为False，需要原始timing数据
    
    # 分析前半部分和后半部分
    first_half = order[:n//2]
    second_half = order[n//2:]
    
    # 检查是否为交替采集（奇偶分离）
    all_odd_first = all(x % 2 == 1 for x in first_half)
    all_even_first = all(x % 2 == 0 for x in first_half)
    all_odd_second = all(x % 2 == 1 for x in second_half)
    all_even_second = all(x % 2 == 0 for x in second_half)
    
    if all_odd_first and all_even_second:
        result["pattern_name"] = "Interleaved (Odd-Even)"
        result["details"] = "Odd slices first (1,3,5...), then even slices (2,4,6...)"
    elif all_even_first and all_odd_second:
        result["pattern_name"] = "Interleaved (Even-Odd)"
        result["details"] = "Even slices first (2,4,6...), then odd slices (1,3,5...)"
    else:
        # 检查是否为顺序采集
        if order == list(range(1, n + 1)):
            result["pattern_name"] = "Sequential (Ascending)"
            result["details"] = "Slices acquired in ascending order (1→N)"
        elif order == list(range(n, 0, -1)):
            result["pattern_name"] = "Sequential (Descending)"
            result["details"] = "Slices acquired in descending order (N→1)"
        else:
            # 检查是否为中心向外或外向中心
            if _is_center_out_pattern(order):
                result["pattern_name"] = "Center-Out"
                result["details"] = "Acquisition from center slices to edge slices"
            elif _is_out_center_pattern(order):
                result["pattern_name"] = "Out-Center"
                result["details"] = "Acquisition from edge slices to center slices"
            else:
                # 检查是否为多带交错
                if _is_multiband_pattern(order):
                    result["pattern_name"] = "Multi-band/SMS"
                    result["details"] = "Simultaneous multi-slice acquisition detected"
                    result["is_multiband"] = True
                else:
                    result["pattern_name"] = "Custom/Non-standard"
                    result["details"] = f"Non-standard pattern. First few: {order[:5]}..."
    
    return result


def _is_center_out_pattern(order: List[int]) -> bool:
    """检查是否为中心向外的采集模式"""
    n = len(order)
    center = n // 2
    
    # 检查前几个采集的slice是否接近中心
    first_few = order[:min(4, n//4)]
    distances = [abs(x - center) for x in first_few]
    
    # 如果前几个slice都接近中心，可能是center-out
    return all(d < n//4 for d in distances)


def _is_out_center_pattern(order: List[int]) -> bool:
    """检查是否为外向中心的采集模式"""
    n = len(order)
    
    # 检查前几个采集的slice是否在边缘
    first_few = order[:min(4, n//4)]
    
    # 如果前几个slice都在边缘（接近1或n），可能是out-center
    return all(x <= 2 or x >= n-1 for x in first_few)


def _is_multiband_pattern(order: List[int]) -> bool:
    """
    检查是否可能为多带模式
    多带采集的特征是某些slice会同时采集
    """
    n = len(order)
    
    # 简单的启发式方法：检查是否有规律的跳跃模式
    # 例如：[1,5,9,13, 2,6,10,14, 3,7,11,15, 4,8,12,16] 对于MB=4
    if n >= 8:
        # 计算前几个元素之间的间隔
        gaps = [order[i+1] - order[i] for i in range(min(4, len(order)-1))]
        # 如果间隔都相等且大于1，可能是多带
        if len(set(gaps)) == 1 and gaps[0] > 1:
            return True
    
    return False


def _format_order_preview(order: List[int], preview_length: int = 8) -> str:
    """格式化采集顺序预览"""
    if len(order) <= preview_length:
        return str(order)
    else:
        preview = order[:preview_length]
        return f"{preview}... (total: {len(order)} slices)"


# 清理全局变量
_last_timing_range = None