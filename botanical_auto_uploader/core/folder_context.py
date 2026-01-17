# core/folder_context.py

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class FolderContext:
    """描述一个 Drive 商品文件夹的原始信息（还没经过 AI 分析）"""

    folder_id: str
    folder_name: str
    created_time: str

    # 解析自文件夹名
    product_type: str = ""
    raw_materials_str: str = ""   # 还没拆成 list
    series: str = ""
    price_from_name: float | None = None

    # Drive 文件信息
    image_files: List[Dict[str, Any]] = field(default_factory=list)  # 每个是 files().list() 返回的 dict
    note_file: Dict[str, Any] | None = None
    other_files: List[Dict[str, Any]] = field(default_factory=list)

    # note.txt 内容（如果有的话）
    note_text: str = ""
