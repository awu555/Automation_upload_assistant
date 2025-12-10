import os
import time
import json
import base64
import requests
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# --- 配置 ---
CLIENT_ID = os.getenv("ETSY_CLIENT_ID")
REFRESH_TOKEN = os.getenv("ETSY_REFRESH_TOKEN")
SHIPPING_ID = int(os.getenv("SHIPPING_PROFILE_ID"))
TAXONOMY_ID = int(os.getenv("TAXONOMY_ID"))
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_KEY)

# 全局变量存储 Access Token
current_access_token = None
current_shop_id = os.getenv("ETSY_SHOP_ID")

# --- 模块 1: Etsy 认证与刷新 ---
def get_valid_headers():
    global current_access_token, REFRESH_TOKEN
    
    # 简单起见，每次运行脚本我们都刷新一次 Token (Token有效期1小时，脚本跑完通常不到1小时)
    if current_access_token:
        return {"x-api-key": CLIENT_ID, "Authorization": f"Bearer {current_access_token}"}
    
    print("🔄 Refreshing Etsy Access Token...")
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": REFRESH_TOKEN
    }
    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data=payload)
    
    if r.status_code != 200:
        raise Exception(f"Token refresh failed: {r.text}")
    
    data = r.json()
    current_access_token = data['access_token']
    REFRESH_TOKEN = data['refresh_token'] # 更新 Refresh Token 以备下次使用(建议写回.env，这里暂存内存)
    
    # 如果 .env 没填 Shop ID，顺便获取一下
    get_shop_id()
    
    return {"x-api-key": CLIENT_ID, "Authorization": f"Bearer {current_access_token}"}

def get_shop_id():
    global current_shop_id
    if current_shop_id: return
    
    headers = {"x-api-key": CLIENT_ID, "Authorization": f"Bearer {current_access_token}"}
    # 获取用户对应的 Shop
    r = requests.get(f"https://api.etsy.com/v3/application/users/{os.getenv('ETSY_CLIENT_ID').split('.')[0]}/shops", headers=headers)
    # 这里的 Endpoint 可能需要根据 User ID 调整，更通用的方法是 Search Shops
    # 但最简单的是你直接去 Etsy 后台看你的 Shop ID 填入 .env
    # 这里假设你已经在 .env 填好了
    pass 

# --- 模块 2: OpenAI 视觉分析 ---
def analyze_images_with_gpt(image_paths, folder_name):
    print(f"🤖 AI Analyzing: {folder_name}...")
    
    # 读取第一张图
    with open(image_paths[0], "rb") as img_file:
        b64_image = base64.b64encode(img_file.read()).decode('utf-8')

    # 解析文件夹名获取价格 (格式: SKU_价格USD_名称)
    try:
        parts = folder_name.split('_')
        price_str = parts[1].replace('USD', '')
        price = float(price_str)
        sku = parts[0]
    except:
        price = 100.00
        sku = "W-UNKNOWN"

    prompt = f"""
    You are an expert Etsy seller for brand 'Wù Essence' (Handmade botanical jewelry).
    Folder Info: {folder_name}. Price context: {price}.
    
    Task: Create Etsy listing JSON.
    1. Title: SEO optimized, include materials (Real flowers, Resin, etc). Max 140 chars.
    2. Description: Poetic, storytelling, mentioning 'handcrafted nature'. Include dimensions estimate.
    3. Tags: List of 13 strings (e.g. 'cottagecore', 'pressed flower').
    4. Materials: List of strings.
    
    Output JSON ONLY:
    {{
        "title": "string",
        "description": "string",
        "price": {price},
        "quantity": 1,
        "tags": ["tag1", "tag2"],
        "materials": ["resin", "brass"],
        "sku": "{sku}"
    }}
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
            ]}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- 模块 3: Etsy 上传 ---
def upload_to_etsy(listing_data, image_paths):
    headers = get_valid_headers()
    shop_id = os.getenv("ETSY_SHOP_ID")
    
    # 1. 创建 Draft Listing
    print(f"📝 Creating Draft: {listing_data['title'][:30]}...")
    payload = {
        "quantity": listing_data['quantity'],
        "title": listing_data['title'],
        "description": listing_data['description'],
        "price": listing_data['price'],
        "who_made": "i_did",
        "when_made": "2020_2025",
        "taxonomy_id": TAXONOMY_ID, 
        "shipping_profile_id": SHIPPING_ID,
        "tags": listing_data['tags'],
        "materials": listing_data['materials'],
        "sku": listing_data['sku'],
        "type": "physical",
        "state": "draft"
    }
    
    r = requests.post(f"https://api.etsy.com/v3/application/shops/{shop_id}/listings", headers=headers, json=payload)
    
    if r.status_code != 201:
        print(f"❌ Failed to create listing: {r.text}")
        return
    
    listing_id = r.json()['listing_id']
    print(f"✅ Draft Created! ID: {listing_id}")
    
    # 2. 上传图片
    upload_url = f"https://api.etsy.com/v3/application/shops/{shop_id}/listings/{listing_id}/images"
    # 上传图片时 header 不含 Content-Type
    img_headers = {"x-api-key": CLIENT_ID, "Authorization": headers['Authorization']}
    
    for idx, img_path in enumerate(image_paths):
        print(f"   ⬆️ Uploading image {idx+1}/{len(image_paths)}...")
        with open(img_path, 'rb') as f:
            files = {'image': f}
            # Etsy 排序从 1 开始
            data = {'rank': idx + 1} 
            r_img = requests.post(upload_url, headers=img_headers, files=files, data=data)
            if r_img.status_code != 201:
                print(f"   ⚠️ Image upload failed: {r_img.text}")
        time.sleep(1) # 限速保护

# --- 主入口 ---
def main():
    root_folder = "./products_to_upload" # 你的图片根目录
    
    # 遍历文件夹
    for folder in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, folder)
        if not os.path.isdir(folder_path): continue
        
        # 收集图片
        images = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('jpg','jpeg','png'))]
        if not images: continue
        
        try:
            # 1. AI 分析
            data = analyze_images_with_gpt(images, folder)
            # 2. Etsy 上传
            upload_to_etsy(data, images)
        except Exception as e:
            print(f"❌ Error processing {folder}: {e}")

if __name__ == "__main__":
    main()
