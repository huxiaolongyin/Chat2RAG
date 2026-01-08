# chat2rag/utils/merge_kwargs.py
import json
from typing import Any, Dict, Optional


def deep_merge_dicts(d1: Dict[Any, Any], d2: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    递归合并两个字典，d2优先覆盖d1。
    对于同一个键，若两个值都是dict，则递归合并，否则用d2的值覆盖d1的。
    返回一个新的合并字典，不修改原始输入。
    """
    result = dict(d1)  # 复制，避免修改原字典
    for k, v2 in d2.items():
        v1 = result.get(k)
        if isinstance(v1, dict) and isinstance(v2, dict):
            result[k] = deep_merge_dicts(v1, v2)
        else:
            result[k] = v2
    return result


def merge_generation_kwargs(
    interface_kwargs: Optional[Dict] = None,
    model_default_kwargs: Optional[Dict] = None,
    app_default_kwargs: Optional[Dict] = None,
) -> Dict:
    """
    合并三个层级的 generation_kwargs，优先级:
    接口输入 > 模型默认配置 > 应用默认配置

    参数均可省略或为 None。

    返回合并后的 dict，不修改原始输入。
    """
    merged: Dict = {}

    # 先填入最低优先级的 app_default_kwargs
    if app_default_kwargs:
        merged = deep_merge_dicts(merged, app_default_kwargs)

    # 再用模型默认的覆盖（如果有）
    if model_default_kwargs:
        merged = deep_merge_dicts(merged, model_default_kwargs)

    # 最后用接口输入的覆盖（如果有）
    if isinstance(interface_kwargs, str):
        interface_kwargs = json.loads(interface_kwargs)
    if interface_kwargs:
        merged = deep_merge_dicts(merged, interface_kwargs)

    return merged


def recursive_tuple_to_dict(obj: Any) -> Any:
    """
    递归将嵌套的元组键值对结构转为字典。
    对非元组类型返回原值。
    """
    if isinstance(obj, tuple):
        # 检查是否是键值对形式，即元素是二元组且所有元素长度都是2
        if all(isinstance(i, tuple) and len(i) == 2 for i in obj):
            return {k: recursive_tuple_to_dict(v) for k, v in obj}
        else:
            # 如果只是普通元组，但不符合键值对结构，则递归转
            return tuple(recursive_tuple_to_dict(i) for i in obj)
    # 不是tuple则原样返回
    return obj
