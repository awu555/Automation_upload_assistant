# platforms/etsy_client.py

from __future__ import annotations

from typing import Dict, Any

from core.product_schema import ProductDraft


def create_draft_listing(product: ProductDraft) -> Dict[str, Any]:
    """
    在 Etsy 上创建草稿商品。
    
    Args:
        product: ProductDraft 对象，包含所有商品信息
    
    Returns:
        包含 listing_id 等信息的字典
    """
    # TODO: 实现 Etsy API 调用
    # 1. 准备 API 请求数据
    # 2. 调用 Etsy API 创建草稿
    # 3. 返回 listing_id 等信息
    pass


def upload_images(listing_id: int, product: ProductDraft) -> Dict[str, Any]:
    """
    上传商品图片到 Etsy listing。
    
    Args:
        listing_id: Etsy listing ID
        product: ProductDraft 对象，包含图片路径信息
    
    Returns:
        上传结果信息
    """
    # TODO: 实现图片上传
    # 1. 读取 product.image_paths 中的图片
    # 2. 调用 Etsy API 上传图片
    # 3. 返回上传结果
    pass


def activate_listing(listing_id: int) -> Dict[str, Any]:
    """
    激活 Etsy listing（从草稿状态发布）。
    
    Args:
        listing_id: Etsy listing ID
    
    Returns:
        激活结果信息
    """
    # TODO: 实现 listing 激活
    # 1. 调用 Etsy API 更新 listing 状态
    # 2. 返回激活结果
    pass



