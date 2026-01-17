# botanical_auto_uploader/run_once.py

from config.settings import STATE_STORE_FILE
from core.state_store import StateStore
from pipeline.loader import find_new_product_folders
from pipeline.processor import process_new_folders_debug


def main():
    state = StateStore(STATE_STORE_FILE)
    
    # 第一步：发现新的文件夹，并标记为 pending
    print("=" * 60)
    print("第一步：发现新文件夹")
    print("=" * 60)
    new_folders = find_new_product_folders()

    if new_folders:
        print(f"\n✨ 发现 {len(new_folders)} 个新文件夹，开始标记为 pending：")
        for folder in new_folders:
            folder_id = folder["id"]
            name = folder["name"]
            created_time = folder.get("createdTime", "N/A")
            print(f"  - {name} ({folder_id}) 创建时间: {created_time}")

            state.mark_folder_status(
                folder_id=folder_id,
                name=name,
                status="pending",
                platforms={},
            )
        print(f"✅ 已将所有新文件夹标记为 pending")
    else:
        print("✅ 没有发现新的文件夹。")

    # 第二步：处理 pending 状态的文件夹
    print("\n" + "=" * 60)
    print("第二步：处理 pending 文件夹")
    print("=" * 60)
    process_new_folders_debug()


if __name__ == "__main__":
    main()

