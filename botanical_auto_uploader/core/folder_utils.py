# core/folder_utils.py

from __future__ import annotations

from typing import Tuple, Optional


def parse_folder_name(name: str) -> Tuple[str, str, str, Optional[float]]:
    """
    解析文件夹名，约定格式：
      {product_type}-{materials}-{series}_{price}

    例如：
      "earing-白芷-宁静系列_25"
      "necklace-松果白五眼果-山丘系列_39.9"

    返回: (product_type, materials_str, series, price_float_or_None)
    """
    # 先按 '_' 从右侧切一刀，拿到价格部分
    if "_" in name:
        left, price_part = name.rsplit("_", 1)
        price_part = price_part.strip()
        try:
            price = float(price_part)
        except ValueError:
            price = None
    else:
        left = name
        price = None

    # 再处理左边的部分，用 '-' 拆成最多三段
    # product_type - materials - series
    parts = left.split("-")
    parts = [p.strip() for p in parts if p.strip()]

    product_type = ""
    materials_str = ""
    series = ""

    if len(parts) == 1:
        # 只有一个名字，就当成系列名
        series = parts[0]
    elif len(parts) == 2:
        product_type, materials_str = parts
    else:
        # len >= 3: 前面为 product_type，最后一个为 series，中间合并为 materials
        product_type = parts[0]
        series = parts[-1]
        materials_str = "-".join(parts[1:-1])

    return product_type, materials_str, series, price
