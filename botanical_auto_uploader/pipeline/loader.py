# pipeline/loader.py

from typing import List, Dict, Any

from config.settings import INBOX_FOLDER_ID, STATE_STORE_FILE
from core.drive_client import DriveClient
from core.state_store import StateStore


def find_new_product_folders() -> List[Dict[str, Any]]:
    """
    返回还未处理的新文件夹列表
    每个元素大致形如：
    {
        "id": "...",
        "name": "...",
        "createdTime": "..."
    }
    """
    drive = DriveClient()
    state = StateStore(STATE_STORE_FILE)

    all_folders = drive.list_subfolders(INBOX_FOLDER_ID)
    processed_ids = state.get_processed_folder_ids()

    # 调试信息：帮助诊断问题
    print(f"\n[调试] 从 Drive 获取到 {len(all_folders)} 个文件夹")
    print(f"[调试] 状态文件中已记录的文件夹ID数量: {len(processed_ids)}")
    if processed_ids:
        print(f"[调试] 已记录的文件夹ID: {list(processed_ids)}")

    new_folders = [f for f in all_folders if f["id"] not in processed_ids]
    print(f"[调试] 过滤后的新文件夹数量: {len(new_folders)}")
    
    return new_folders
