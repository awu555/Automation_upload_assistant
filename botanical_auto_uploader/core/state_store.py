# core/state_store.py

import json
from pathlib import Path
from typing import Dict, Any, Set, List


class StateStore:
    """
    用本地 JSON 文件简单记录处理状态：
    {
        "folders": {
            "folder_id_1": {
                "name": "...",
                "status": "success" / "failed",
                "platforms": {
                    "etsy": {
                        "listing_id": "...",
                        "url": "...",
                        "status": "draft"
                    }
                }
            },
            ...
        }
    }
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._state: Dict[str, Any] = {"folders": {}}
        self._load()

    def _load(self) -> None:
        if self.filepath.exists():
            try:
                with self.filepath.open("r", encoding="utf-8") as f:
                    self._state = json.load(f)
                # 确保 _state 有 folders 键
                if "folders" not in self._state:
                    self._state["folders"] = {}
            except Exception as e:
                # 如果损坏就重新初始化（也可以选择抛异常）
                print(f"[警告] 加载状态文件失败: {e}")
                self._state = {"folders": {}}
        else:
            self._state = {"folders": {}}

    def _save(self) -> None:
        with self.filepath.open("w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    # --- 对外方法 ---

    def get_processed_folder_ids(self) -> Set[str]:
        """返回所有已经存在记录的 folder_id（不管成功失败）"""
        return set(self._state.get("folders", {}).keys())

    def get_folder_record(self, folder_id: str) -> Dict[str, Any]:
        return self._state.get("folders", {}).get(folder_id, {})

    def mark_folder_status(
        self,
        folder_id: str,
        name: str,
        status: str,
        platforms: Dict[str, Any] | None = None,
    ) -> None:
        """
        status: "pending" / "success" / "failed"
        platforms: 如 {"etsy": {"listing_id": "...", "status": "draft"}}
        """
        if "folders" not in self._state:
            self._state["folders"] = {}
        self._state["folders"][folder_id] = {
            "name": name,
            "status": status,
            "platforms": platforms or {},
        }
        self._save()

    def list_unfinished_folders(self, status_filter: List[str] | None = None) -> Dict[str, Any]:
        """
        找出还没成功的（比如 pending / failed），
        方便以后做重试逻辑。
        """
        status_filter = status_filter or ["pending", "failed"]
        result = {}
        folders = self._state.get("folders", {})
        
        # 调试信息
        print(f"[调试] list_unfinished_folders: 检查 {len(folders)} 个文件夹")
        print(f"[调试] status_filter: {status_filter}")
        
        for fid, rec in folders.items():
            status = rec.get("status")
            print(f"[调试] 文件夹 {fid}: status={status} (type: {type(status)}), 是否在过滤器中: {status in status_filter}")
            if status in status_filter:
                result[fid] = rec
                print(f"[调试] ✓ 文件夹 {fid} 被添加到结果中")
        
        return result
