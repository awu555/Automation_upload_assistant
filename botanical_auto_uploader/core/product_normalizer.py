# core/product_normalizer.py

from __future__ import annotations

import re
from typing import Dict, Any, List

from core.product_schema import ProductDraft
from core.folder_context import FolderContext


# 中文材料名到英文的映射
MATERIALS_MAPPING: Dict[str, str] = {
    "白芷": "white angelica root",
    "甘草": "licorice root",
    "松果": "pine cone",
    "桉树果": "eucalyptus pod",
    "五眼果": "five-eye fruit",
    "白五眼果": "white five-eye fruit",
    "黑五眼果": "black five-eye fruit",
    "松针": "pine needle",
    "银杏叶": "ginkgo leaf",
    "枫叶": "maple leaf",
    "树脂": "resin",
    "合金": "alloy",
    "金属": "metal",
    "银": "silver",
    "金": "gold",
    "铜": "copper",
}


def translate_material(chinese_name: str) -> str:
    """
    将中文材料名翻译为英文，如果找不到映射则返回原字符串。
    """
    chinese_name = chinese_name.strip()
    return MATERIALS_MAPPING.get(chinese_name, chinese_name)


def clean_title(title: str) -> str:
    """
    清洗标题：
    - 去除换行符和多余空格
    - 统一大小写（首字母大写，其余小写，但保留专有名词）
    """
    if not title:
        return ""
    
    # 去除换行符，替换为空格
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()
    
    # 基本的大小写处理：首字母大写
    # 注意：这里保持简单，复杂的专有名词处理可以后续优化
    if title:
        title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
    
    return title


def clean_tags(tags: List[str], max_count: int = 13) -> List[str]:
    """
    清洗标签：
    - 去除空标签
    - 限制数量（最多 13 个，Etsy 要求）
    - 转换为小写
    - 去重
    """
    if not tags:
        return []
    
    # 清洗：去空、去重、转小写
    cleaned = []
    seen = set()
    for tag in tags:
        tag = tag.strip().lower()
        if tag and tag not in seen:
            cleaned.append(tag)
            seen.add(tag)
            if len(cleaned) >= max_count:
                break
    
    return cleaned


def clean_materials(materials: List[str], folder_ctx: FolderContext) -> List[str]:
    """
    清洗材料列表：
    - 合并 AI 返回的材料和文件夹名中的材料
    - 中文材料名翻译为英文
    - 去重
    """
    all_materials = set()
    
    # 1. 添加 AI 返回的材料
    for mat in materials:
        if mat:
            mat = mat.strip()
            # 尝试翻译中文材料名
            translated = translate_material(mat)
            all_materials.add(translated)
    
    # 2. 从文件夹名解析的材料
    if folder_ctx.raw_materials_str:
        # 可能包含多个材料，用 "-" 或 "," 分隔
        raw_materials = re.split(r'[-,\s]+', folder_ctx.raw_materials_str)
        for mat in raw_materials:
            mat = mat.strip()
            if mat:
                translated = translate_material(mat)
                all_materials.add(translated)
    
    return sorted(list(all_materials))


def build_description(ai_description: str, folder_ctx: FolderContext) -> str:
    """
    构建完整描述：
    - AI 生成的描述
    - 默认保养说明
    """
    parts = []
    
    # 1. AI 生成的描述
    if ai_description:
        parts.append(ai_description.strip())
    
    # 2. 默认保养说明
    care_instructions = """
    
Care Instructions:
- Store in a dry place away from direct sunlight
- Avoid contact with water and chemicals
- Clean gently with a soft, dry cloth
- Handle with care as botanical materials are delicate
"""
    parts.append(care_instructions.strip())
    
    return "\n\n".join(parts)


def normalize_product(ai_json: Dict[str, Any], folder_ctx: FolderContext) -> ProductDraft:
    """
    将 AI 返回的 JSON 和文件夹上下文合并，生成标准化的 ProductDraft。
    
    Args:
        ai_json: OpenAI 返回的 JSON 数据
        folder_ctx: 文件夹上下文，包含解析的文件夹名信息
    
    Returns:
        标准化的 ProductDraft 对象
    """
    # 1. 合并文件夹名解析数据
    # 优先使用 AI 返回的值，如果 AI 没有或为空，则使用文件夹名解析的值
    
    product_type = ai_json.get("product_type") or folder_ctx.product_type or ""
    series = ai_json.get("series") or folder_ctx.series or ""
    price = ai_json.get("price")
    if price is None or price <= 0:
        price = folder_ctx.price_from_name or 0.0
    
    # 2. 字段清洗
    title = clean_title(ai_json.get("title", ""))
    if not title:
        # 如果 AI 没有生成标题，使用文件夹名
        title = folder_ctx.folder_name
    
    description = build_description(
        ai_json.get("description", ""),
        folder_ctx
    )
    
    short_description = ai_json.get("short_description", "").strip()
    if not short_description:
        short_description = title  # 如果没有，使用标题
    
    # 清洗标签（最多 13 个）
    tags = clean_tags(ai_json.get("tags", []), max_count=13)
    
    # 清洗材料（合并 AI 和文件夹名中的材料）
    materials = clean_materials(
        ai_json.get("materials", []),
        folder_ctx
    )
    
    # 清洗颜色
    colors = [c.strip().lower() for c in ai_json.get("colors", []) if c.strip()]
    
    # 3. 设置默认值
    currency = ai_json.get("currency", "USD")
    quantity = ai_json.get("quantity", 1)
    who_made = ai_json.get("who_made", "i_did")
    when_made = ai_json.get("when_made", "made_to_order")
    
    # 4. 其他字段
    style = ai_json.get("style", "").strip()
    category = ai_json.get("category") or product_type or ""
    
    # 5. 品牌信息（默认值）
    brand_name = "Wu Essence"
    
    # 6. 构建 ProductDraft
    product = ProductDraft(
        id=ai_json.get("id_from_drive", folder_ctx.folder_id),
        title=title,
        description=description,
        short_description=short_description,
        price=float(price),
        currency=currency,
        quantity=quantity,
        tags=tags,
        materials=materials,
        colors=colors,
        style=style,
        product_type=product_type,
        category=category,
        series=series,
        brand_name=brand_name,
        care_instructions="Store in a dry place away from direct sunlight. Avoid contact with water and chemicals.",
        handmade=True,
        made_to_order=True,
        who_made=who_made,
        when_made=when_made,
        raw_ai_json=ai_json,
        notes=folder_ctx.note_text or "",
    )
    
    return product

