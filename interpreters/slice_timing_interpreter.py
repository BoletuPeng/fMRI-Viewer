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
        
        # 将采集顺序转换为类MATLAB表达式
        matlab_expression = _convert_to_matlab_expression(acquisition_order)
        
        # 获取额外的序列信息
        image_type = str(context.get("image_type", "")).upper()
        is_mosaic = "MOSAIC" in image_type
        
        # 构建返回结果
        results = {
            "Slice Timing Available": "Yes",
            "Slice Timing Source": "Siemens MosaicRefAcqTimes (0019,1029)",
            "Number of Slices": str(len(acquisition_order)),
            "Acquisition Order": matlab_expression,
            "Image Type": "Mosaic" if is_mosaic else "Standard",
        }
        
        # 如果有timing范围信息
        if '_last_timing_range' in globals():
            min_t, max_t = _last_timing_range
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


def _convert_to_matlab_expression(order: List[int]) -> str:
    """
    将采集顺序转换为类MATLAB表达式
    
    参数:
        order: 采集顺序列表
        
    返回:
        str: 类MATLAB表达式，如 "[31:-2:1,32:-2:2]" 或原始列表
    """
    if not order:
        return "[]"
    
    if len(order) < 4:
        # 少于4个元素，直接返回原始列表
        return str(order)
    
    # 存储找到的等差数列段
    segments = []
    i = 0
    
    while i < len(order):
        # 尝试从当前位置找等差数列
        found = False
        
        # 如果剩余元素少于4个，直接添加剩余元素
        if i + 3 >= len(order):
            for j in range(i, len(order)):
                segments.append(str(order[j]))
            break
        
        # 从当前位置开始，尝试找到等差数列
        for start in range(i, min(i + 1, len(order) - 3)):
            if start + 3 >= len(order):
                break
                
            # 检查从start开始的四个元素是否构成等差数列
            diff1 = order[start + 1] - order[start]
            diff2 = order[start + 2] - order[start + 1]
            diff3 = order[start + 3] - order[start + 2]
            
            if diff1 == diff2 == diff3 and diff1 != 0:
                # 找到等差数列，继续扩展
                step = diff1
                end_idx = start + 3
                
                # 继续查找符合等差数列的元素
                while end_idx + 1 < len(order):
                    expected_next = order[end_idx] + step
                    if order[end_idx + 1] == expected_next:
                        end_idx += 1
                    else:
                        break
                
                # 生成MATLAB表达式
                if step == 1:
                    # 步长为1，可以简化为 start:end
                    segments.append(f"{order[start]}:{order[end_idx]}")
                elif step == -1:
                    # 步长为-1，简化为 start:-1:end
                    segments.append(f"{order[start]}:{order[end_idx]}")
                else:
                    # 一般情况 start:step:end
                    segments.append(f"{order[start]}:{step}:{order[end_idx]}")
                
                i = end_idx + 1
                found = True
                break
        
        if not found:
            # 当前位置无法形成等差数列，添加单个元素
            segments.append(str(order[i]))
            i += 1
    
    # 如果没有找到任何等差数列（所有都是单个元素），返回完整列表
    if all(seg.isdigit() or (seg.startswith('-') and seg[1:].isdigit()) for seg in segments):
        return str(order)
    
    # 返回MATLAB风格的表达式
    return "[" + ",".join(segments) + "]"


# 清理全局变量
_last_timing_range = None