# core/ai_analyzer.py

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict, Any

from openai import OpenAI

from core.folder_context import FolderContext


def _encode_image_to_base64(image_path: Path) -> str:
    """将图片文件编码为 base64 字符串"""
    with image_path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_format(image_path: Path) -> str:
    """根据文件扩展名返回图片格式"""
    ext = image_path.suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        return "jpeg"
    elif ext == ".png":
        return "png"
    elif ext == ".gif":
        return "gif"
    elif ext == ".webp":
        return "webp"
    else:
        return "jpeg"  # 默认

def build_prompt_for_product(ctx: FolderContext) -> str:
    """
    根据文件夹上下文，构造发给 OpenAI 的文字 Prompt。
    """
    product_type = ctx.product_type or ""
    materials_raw = ctx.raw_materials_str or ""
    series = ctx.series or ""
    price_from_name = ctx.price_from_name
    notes = ctx.note_text or ""

    # 你可以根据自己品牌调整下面这段描述风格
    prompt = f"""
你是一位擅长 Etsy 文案和自然系手作商品描述的助手，店铺品牌叫做 "Wù Essence"，
主要出售使用木材、果实、种子、干花、中草药植物等原材料制作的自然风首饰与装饰品
（如耳环、项链、挂饰、家居挂件等）。

你的任务是：在保持统一品牌气质的前提下，为每个商品生成适合 Etsy 的文案。
品牌气质关键词：forest-inspired, botanical, poetic, calm, spiritual, natural, one-of-a-kind。

⚠️ 品牌与合规要求（非常重要）：
- 文案可以带有诗意和灵性氛围，但只能描述「情绪感受」和「氛围」，例如：calm, grounding, peaceful, connected to nature。
- 严禁出现任何涉及「治疗、药效、保健功效」的词汇或暗示，例如：heal, healing, cure, treat, pain relief, anxiety relief, improve sleep, anti-inflammatory, detox 等。
- 不要使用「medical, medicine, remedy, therapy, TCM, traditional Chinese medicine」等字眼。
- 可以提到植物的「象征意义 / cultural meaning / symbolic meaning」，但不要写会带来具体健康功效。
- 不要做夸张承诺（如：guaranteed, miracle, life-changing），用温和、诚实的描述。
- 文案整体语气要温柔、自然、真诚，有手作质感，避免像硬广或营销文案。

现在你会看到一张首饰或装饰品的产品图片，以及一些额外的文本信息。
请你基于这些信息，生成一份结构化的 JSON，用来在 Etsy 上上架商品，
同时这个 JSON 也要尽可能通用，方便未来在其他平台复用。

【文件夹信息】
- folder_id: {ctx.folder_id}
- folder_name: {ctx.folder_name}

【从文件夹名解析出的字段（仅供参考，可以修正补充）】
- product_type: {product_type}
- materials_raw: {materials_raw}
- series: {series}
- price_from_name: {price_from_name}

【额外备注（可能为空）】
{notes or "（无）"}

【图片说明】
- 图片是一件首饰或装饰品的产品图，请仔细观察：类型（耳饰/项链/挂件/摆件等）、材质（植物/木头/金属/树脂等）、颜色、整体风格。

⚠️ 输出要求：
1. 你必须返回一个 **合法的 JSON 对象**（不包含任何多余文字），键名使用英文，值可以是英文或中英混合，但整体以英文为主。
2. 不要输出注释，不要包裹在代码块中。
3. `price` 使用数字（float），货币统一用 "USD"。
4. `quantity` 先默认 1。
5. `tags` 是一个字符串数组，用于 Etsy 标签，数量不超过 13，注意是英文小写为主，可以少量中英文混合，贴合自然 / botanical / forest / handmade 主题。
6. `materials` 是一个数组，需要尽量准确描述作品中使用到的材料，特别是木材、果实、种子、干花、草本等自然材料。
7. 文案中不要提及任何医疗、保健或疗愈功效，只能描述美感、气质、氛围和使用场景。

请严格按照下面的 JSON 结构返回（键名固定）：

{{
  "id_from_drive": "{ctx.folder_id}",
  "title": "英文为主、简洁且有卖点的标题，可以适当包含系列名和材质，如 botanical wood & seed wall hanging",
  "description": "完整的 Etsy 描述，包含材质、尺寸或大致尺寸、设计灵感、使用/佩戴场景、保养建议等（可以中英混合，但以英文为主，语气自然、温和、不提任何药效或治疗功效）",
  "short_description": "一句话概括这个作品的特点（英文为主，突出 natural / botanical / handcrafted / one-of-a-kind 等卖点）",
  "price": {price_from_name if price_from_name is not None else 0.0},
  "currency": "USD",
  "quantity": 1,
  "tags": [
    "botanical jewelry",
    "wood and herbal art"
  ],
  "materials": [
    "natural wood",
    "botanical elements"
  ],
  "colors": [
    "brown",
    "green"
  ],
  "style": "forest-inspired, natural, botanical, poetic",
  "product_type": "{product_type}",
  "category": "{product_type}",
  "series": "{series}",
  "who_made": "i_did",
  "when_made": "made_to_order"
}}

注意：
- 如果你认为文件夹名中的 product_type / materials / series 不准确，可以在 JSON 中给出你修正后的版本。
- 如果 price_from_name 看起来不合理，你可以在 JSON 中合理修改 price。
- 请确保返回值是 **严格的 JSON 对象**，不要有任何多余注释或文字。
"""
    return prompt


def _get_openai_api_key() -> str:
    """
    获取 OpenAI API Key，按优先级尝试：
    1. 环境变量 OPENAI_API_KEY
    2. 配置文件 config/credentials/openai_key.txt（如果存在）
    
    Returns:
        API key 字符串
    
    Raises:
        RuntimeError: 如果找不到 API key
    """
    # 方法1: 从环境变量读取
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # 调试信息：显示是否读取到（但不显示完整 key）
        key_preview = api_key[:8] + "..." if len(api_key) > 8 else "***"
        print(f"  [调试] 从环境变量读取到 OPENAI_API_KEY: {key_preview}")
        return api_key.strip()
    
    # 方法2: 从配置文件读取
    from config.settings import BASE_DIR
    key_file = BASE_DIR / "config" / "credentials" / "openai_key.txt"
    if key_file.exists():
        try:
            api_key = key_file.read_text(encoding="utf-8").strip()
            if api_key:
                print(f"  [调试] 从配置文件读取到 OPENAI_API_KEY: {api_key[:8]}...")
                return api_key
        except Exception as e:
            print(f"  [警告] 读取配置文件失败: {e}")
    
    # 如果都找不到，提供详细的错误信息
    print("\n❌ 错误：找不到 OPENAI_API_KEY")
    print("   请使用以下方式之一设置 API Key：")
    print("   1. 设置环境变量: export OPENAI_API_KEY='your-key-here'")
    print("   2. 创建配置文件: config/credentials/openai_key.txt（内容就是你的 API key）")
    print(f"   当前环境变量 OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', '未设置')}")
    raise RuntimeError("请先设置 OPENAI_API_KEY（环境变量或配置文件）")


def call_openai_for_product(
    ctx: FolderContext, 
    main_image_path: Path, 
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    调用 OpenAI（带图像）生成商品 JSON。
    
    Args:
        ctx: 文件夹上下文
        main_image_path: 主图的本地路径（已下载）
        model: OpenAI 模型名称，默认使用 gpt-4o-mini（支持视觉）
    
    Returns:
        解析后的 JSON dict，包含 id_from_drive, title, description, price, tags, materials 等字段
    
    注意：需要环境变量 OPENAI_API_KEY 已设置，或创建 config/credentials/openai_key.txt 文件。
    """
    api_key = _get_openai_api_key()

    if not main_image_path.exists():
        raise FileNotFoundError(f"主图文件不存在: {main_image_path}")

    print(f"  [调试] 使用模型: {model}")
    client = OpenAI(api_key=api_key)

    b64_image = _encode_image_to_base64(main_image_path)
    image_format = _get_image_format(main_image_path)
    prompt = build_prompt_for_product(ctx)

    # 使用标准的 chat.completions.create API with vision
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{b64_image}"
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
    )

    # 从 response 中取出 JSON 字符串并解析
    json_str = response.choices[0].message.content
    if not json_str:
        raise RuntimeError("OpenAI 返回的内容为空")

    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as e:
        raise RuntimeError(f"解析 OpenAI 返回的 JSON 失败: {e}\n原始内容: {json_str}")

