# pipeline/processor.py

from __future__ import annotations

import json
from pprint import pprint
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from config.settings import STATE_STORE_FILE, BASE_DIR, TEMP_DIR, AI_RESULTS_DIR, EXPORT_DIR
from core.drive_client import DriveClient
from core.state_store import StateStore
from core.folder_context import FolderContext
from core.ai_analyzer import call_openai_for_product
from core.product_normalizer import normalize_product
from core.product_schema import ProductDraft
from core.etsy_exporter import export_products_to_csv, export_products_to_excel


def parse_folder_name(name: str) -> Dict[str, Any]:
    """
    按约定解析文件夹名:
    {product_type}-{materials}-{series}_{price}

    例: 'earring-白芷-宁静系列_25'
    """
    name = name.strip()

    # 先按 '_' 拆出价格部分
    base_part, sep, price_part = name.rpartition("_")
    price: float | None = None
    if sep:  # 找到了 '_'
        try:
            price = float(price_part)
        except ValueError:
            price = None
    else:
        base_part = name  # 没有 '_', 全部作为前半部分

    # 再按 '-' 拆 product_type / materials / series
    # 最多分成 3 段，多出来的都进最后一段
    parts = base_part.split("-", 2)
    product_type = parts[0].strip() if len(parts) > 0 else ""
    materials_raw = parts[1].strip() if len(parts) > 1 else ""
    series = parts[2].strip() if len(parts) > 2 else ""

    return {
        "product_type": product_type,
        "materials_raw": materials_raw,
        "series": series,
        "price": price,
    }


def classify_files(files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    根据 mimeType 把文件分成图片 / 其他
    """
    images: List[Dict[str, Any]] = []
    others: List[Dict[str, Any]] = []

    for f in files:
        mime = f.get("mimeType", "")
        if mime.startswith("image/"):
            images.append(f)
        else:
            others.append(f)

    return {"images": images, "others": others}


def download_main_image_debug(
    drive: DriveClient,
    folder_id: str,
    folder_name: str,
    first_image: Dict[str, Any],
) -> Path:
    """
    调试用：下载主图到本地，看路径是否正常。
    downloads/{folder_id}/{filename}
    """
    print(f"  [调试] download_main_image_debug 函数被调用")
    print(f"  [调试] folder_id: {folder_id}, folder_name: {folder_name}")
    print(f"  [调试] first_image: {first_image}")
    
    download_dir = BASE_DIR / "downloads" / folder_id
    dest_path = download_dir / first_image["name"]
    print(f"  [调试] 目标路径: {dest_path}")
    
    print(f"  [调试] 开始调用 drive.download_file...")
    drive.download_file(first_image["id"], dest_path)
    print(f"  ✅ 主图已下载到: {dest_path}")
    return dest_path


def build_folder_context(
    folder_meta: Dict[str, Any], 
    drive: DriveClient
) -> tuple[FolderContext, Path]:
    """
    根据 folder_meta 构建 FolderContext 并下载主图。
    
    Args:
        folder_meta: 包含 id, name, createdTime 的文件夹元数据
        drive: DriveClient 实例
    
    Returns:
        (FolderContext, main_image_path) 元组
    """
    folder_id = folder_meta["id"]
    folder_name = folder_meta["name"]
    created_time = folder_meta.get("createdTime", "")

    # 1. 列出文件，找到第一张图片作为主图
    files = drive.list_files_in_folder(folder_id)
    if not files:
        raise RuntimeError(f"文件夹 {folder_name} 中没有文件。")

    classified = classify_files(files)
    image_files = classified["images"]
    other_files = classified["others"]

    if not image_files:
        raise RuntimeError(f"文件夹 {folder_name} 中没有找到图片文件。")

    main_image_file = image_files[0]

    # 2. 下载主图到本地临时目录
    # 使用临时目录，文件名使用 folder_id 和原文件名
    tmp_dir = TEMP_DIR / "images"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取原文件扩展名，如果没有则默认 .jpg
    original_name = main_image_file.get("name", "image")
    original_ext = Path(original_name).suffix or ".jpg"
    dest_path = tmp_dir / f"{folder_id}_main{original_ext}"

    print(f"  📥 下载主图: {main_image_file['name']} -> {dest_path}")
    drive.download_file(main_image_file["id"], dest_path)

    # 3. 解析文件夹名
    parsed = parse_folder_name(folder_name)
    
    # 4. 查找并读取 note.txt（如果有）
    note_file = None
    note_text = ""
    for f in other_files:
        if f.get("name", "").lower() in ["note.txt", "notes.txt", "note"]:
            note_file = f
            # 下载并读取 note.txt 内容
            note_path = tmp_dir / f"{folder_id}_note.txt"
            drive.download_file(f["id"], note_path)
            try:
                note_text = note_path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  ⚠️ 读取 note.txt 失败: {e}")
            break

    # 5. 构建 FolderContext
    ctx = FolderContext(
        folder_id=folder_id,
        folder_name=folder_name,
        created_time=created_time,
        product_type=parsed.get("product_type", ""),
        raw_materials_str=parsed.get("materials_raw", ""),
        series=parsed.get("series", ""),
        price_from_name=parsed.get("price"),  # parse_folder_name 返回的是 "price"
        image_files=image_files,
        note_file=note_file,
        other_files=other_files,
        note_text=note_text,
    )

    return ctx, dest_path


def process_new_folders_debug() -> None:
    """
    调试版处理函数：
    - 读取 state.json 中 status == 'pending' 的文件夹
    - 对每个文件夹:
        * 构造 FolderContext
        * 调用 OpenAI 生成商品 JSON
        * 转换为 ProductDraft
        * 收集所有产品用于导出
    - 最后导出为 CSV/Excel 文件
    """
    state = StateStore(STATE_STORE_FILE)
    drive = DriveClient()

    # 获取 pending 状态的文件夹
    pending_records = state.list_unfinished_folders(status_filter=["pending"])
    if not pending_records:
        print("✅ 当前没有 pending 状态的文件夹需要处理。")
        return

    print(f"🔍 发现 {len(pending_records)} 个 pending 文件夹，开始处理...\n")

    # 收集所有处理成功的产品
    products_for_export: List[tuple[ProductDraft, List[Dict[str, Any]]]] = []

    for folder_id, rec in pending_records.items():
        folder_name = rec.get("name", "")
        print(f"\n🗂 处理文件夹: {folder_name} ({folder_id})")

        try:
            # 从 Drive 获取文件夹的完整信息（包括 createdTime）
            # 注意：我们需要从父目录列表中查找这个文件夹，或者直接使用已知信息
            # 为了简化，我们使用 state 中已有的信息，createdTime 可以从 Drive 获取或使用默认值
            folder_meta = {
                "id": folder_id,
                "name": folder_name,
                "createdTime": rec.get("createdTime", ""),  # 如果 state 中没有，就留空
            }

            # 构造 FolderContext
            print("📂 构建 FolderContext...")
            ctx, main_image_path = build_folder_context(folder_meta, drive)
            
            print("📂 解析后的 FolderContext：")
            print(f"  - folder_id: {ctx.folder_id}")
            print(f"  - folder_name: {ctx.folder_name}")
            print(f"  - product_type: {ctx.product_type}")
            print(f"  - raw_materials_str: {ctx.raw_materials_str}")
            print(f"  - series: {ctx.series}")
            print(f"  - price_from_name: {ctx.price_from_name}")
            print(f"  - 图片数量: {len(ctx.image_files)}")
            print(f"  - 主图路径: {main_image_path}")

            # === 这里正式进入 AI 阶段 ===
            print("\n🤖 调用 OpenAI 生成商品 JSON...")
            ai_data = call_openai_for_product(ctx, main_image_path)
            
            print("\n✅ OpenAI 返回 JSON：")
            pprint(ai_data)

            # 保存 AI 返回的 JSON 到文件
            ai_result_file = AI_RESULTS_DIR / f"{folder_id}.json"
            with ai_result_file.open("w", encoding="utf-8") as f:
                json.dump(ai_data, f, ensure_ascii=False, indent=2)
            print(f"💾 AI 结果已保存到: {ai_result_file}")

            # === 使用 normalizer 转换为 ProductDraft ===
            print("\n🔧 使用 normalizer 转换为 ProductDraft...")
            final_product = normalize_product(ai_data, ctx)
            print("\n✅ 最终 ProductDraft：")
            print(f"  ID: {final_product.id}")
            print(f"  标题: {final_product.title}")
            print(f"  价格: {final_product.currency} {final_product.price}")
            print(f"  类型: {final_product.product_type}")
            print(f"  系列: {final_product.series}")
            print(f"  标签 ({len(final_product.tags)}): {', '.join(final_product.tags[:5])}{'...' if len(final_product.tags) > 5 else ''}")
            print(f"  材料 ({len(final_product.materials)}): {', '.join(final_product.materials[:5])}{'...' if len(final_product.materials) > 5 else ''}")
            print(f"  颜色: {', '.join(final_product.colors) if final_product.colors else 'N/A'}")
            print(f"  描述长度: {len(final_product.description)} 字符")
            print(f"\n完整 ProductDraft 对象：")
            pprint(final_product)

            # 收集产品用于导出（包含图片文件信息）
            products_for_export.append((final_product, ctx.image_files))

        except Exception as e:
            print(f"❌ 处理文件夹 {folder_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue

        print("")  # 空行分隔一下

    # === 导出所有产品为 CSV/Excel ===
    if products_for_export:
        print("\n" + "=" * 60)
        print("导出 Etsy 填写表格")
        print("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 导出 CSV
        csv_path = EXPORT_DIR / f"etsy_products_{timestamp}.csv"
        try:
            export_products_to_csv(products_for_export, csv_path)
            print(f"✅ CSV 文件已导出: {csv_path}")
        except Exception as e:
            print(f"❌ 导出 CSV 失败: {e}")
        
        # 导出 Excel（如果安装了 openpyxl）
        excel_path = EXPORT_DIR / f"etsy_products_{timestamp}.xlsx"
        try:
            export_products_to_excel(products_for_export, excel_path)
            print(f"✅ Excel 文件已导出: {excel_path}")
        except ImportError as e:
            print(f"⚠️  跳过 Excel 导出（需要安装 openpyxl: pip install openpyxl）")
        except Exception as e:
            print(f"❌ 导出 Excel 失败: {e}")
        
        print(f"\n📋 共导出 {len(products_for_export)} 个产品")
        print(f"   文件位置: {EXPORT_DIR}")
    else:
        print("\n⚠️  没有成功处理的产品，无法导出。")
