# config/settings.py

from pathlib import Path

# 项目根目录（你可以按需要调整）
BASE_DIR = Path(__file__).resolve().parent.parent

# === Google Drive 相关配置 ===
# 你在 Google Cloud 上下载的 OAuth 客户端 JSON 放在 config/credentials 目录
GOOGLE_CREDENTIALS_FILE = BASE_DIR / "config" / "credentials" / "google_credentials.json"
GOOGLE_TOKEN_FILE = BASE_DIR / "config" / "credentials" / "google_token.json"

# Drive 访问权限范围（只读够用，如果之后要写可以改）
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# 产品入口父目录的 folder id（你需要手动填上去）
# 比如：https://drive.google.com/drive/folders/XXXXXX 中的 XXXXXX
INBOX_FOLDER_ID = "1VoKLALtvk3QwXlRFMQElEBgndzyL15u9"  # TODO: 替换成真实的

# === 状态存储 ===
STATE_STORE_FILE = BASE_DIR / "data" / "state.json"
STATE_STORE_FILE.parent.mkdir(exist_ok=True, parents=True)

# config/settings.py 末尾追加

# 用来存放从 Drive 临时下载的文件（比如主图）
TEMP_DIR = BASE_DIR / "tmp"
TEMP_DIR.mkdir(exist_ok=True, parents=True)

# 用来存放 AI 分析结果的目录
AI_RESULTS_DIR = BASE_DIR / "data" / "ai_results"
AI_RESULTS_DIR.mkdir(exist_ok=True, parents=True)

# 用来存放 Etsy 导出文件的目录
EXPORT_DIR = BASE_DIR / "data" / "exports"
EXPORT_DIR.mkdir(exist_ok=True, parents=True)
