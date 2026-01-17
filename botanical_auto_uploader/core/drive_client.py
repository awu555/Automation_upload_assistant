# core/drive_client.py

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config.settings import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE, GOOGLE_SCOPES


class DriveClient:
    def __init__(self):
        self.creds = self._get_credentials()
        self.service = build("drive", "v3", credentials=self.creds)

    def _get_credentials(self) -> Credentials:
        creds = None
        if GOOGLE_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), GOOGLE_SCOPES)
        # 如果没有 token 或过期，就重新授权
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(GOOGLE_CREDENTIALS_FILE),
                    GOOGLE_SCOPES,
                )
                creds = flow.run_local_server(port=0)
            # 保存 token 供下次使用
            with GOOGLE_TOKEN_FILE.open("w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return creds

    # --- 1. 列出父目录下的子文件夹 ---

    def list_subfolders(self, parent_folder_id: str) -> List[Dict[str, Any]]:
        """
        返回指定父目录下一层子文件夹列表
        每个元素包含：id, name, createdTime
        """
        query = (
            f"'{parent_folder_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name, createdTime)",
                orderBy="createdTime",
            )
            .execute()
        )
        return results.get("files", [])

    # --- 2. 列出某个文件夹中的文件 ---

    def list_files_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        返回某文件夹下所有文件（不区分类型）
        每个元素包含：id, name, mimeType
        """
        query = f"'{folder_id}' in parents and trashed = false"
        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType, createdTime)",
                orderBy="createdTime",
            )
            .execute()
        )
        return results.get("files", [])

    # --- 3. 下载文件到本地 ---

    def download_file(self, file_id: str, dest_path: Path) -> Path:
        """
        下载指定 file_id 到 dest_path
        """
        from googleapiclient.http import MediaIoBaseDownload
        import io

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(dest_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return dest_path
