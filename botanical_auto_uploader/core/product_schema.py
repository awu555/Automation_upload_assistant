from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ProductDraft:
    """产品草稿数据结构"""
    
    id: str
    title: str
    description: str
    short_description: str
    price: float
    currency: str
    quantity: int
    tags: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    style: str = ""
    product_type: str = ""
    category: str = ""
    series: str = ""
    
    brand_name: str = ""
    story: str = ""
    care_instructions: str = ""
    handmade: bool = False
    made_to_order: bool = False
    
    image_paths: List[str] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    main_image_index: int = 0
    
    dimensions: Dict[str, Any] = field(default_factory=dict)
    weight: float = 0.0
    unit: str = ""
    
    who_made: str = ""
    when_made: str = ""
    taxonomy_id: int = 0
    shop_section_id: int = 0
    
    hashtags: List[str] = field(default_factory=list)
    video_paths: List[str] = field(default_factory=list)
    variants: Dict[str, Any] = field(default_factory=dict)
    seo_title: str = ""
    seo_description: str = ""
    
    raw_ai_json: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
