import json
import sys
from datetime import datetime
from curl_cffi import requests

API_URL = "https://s8tv002.com/api/fixtures/base"
IMAGE_BASE = "https://s8tvkc.top/wp-json/s8-image/"
STREAM_HLS_BASE = "https://hls.lauthaitv.cc/live/"
STREAM_FLV_BASE = "https://flv.lauthaitv.cc/live/"

# Danh sách Proxy dự phòng (có thể thay bằng Proxy cá nhân nếu có)
PROXIES_LIST = [
    None, # Thử kết nối trực tiếp trước
    "http://103.152.112.162:80",
    "http://43.134.68.170:3128",
    "http://18.141.211.200:80"
]

def get_group_title(competition_name):
    if not competition_name:
        return "Bóng đá"
    name_lower = competition_name.lower()
    if any(kw in name_lower for kw in ["volleyball", "bóng chuyền"]): return "Bóng chuyền"
    if any(kw in name_lower for kw in ["basketball", "bóng rổ", "nba"]): return "Bóng rổ"
    if any(kw in name_lower for kw in ["tennis", "quần vợt"]): return "Tennis"
    return "Bóng đá"

def fetch_data_with_fallback():
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://s8tv002.com",
        "Referer": "https://s8tv002.com/",
    }
    
    for proxy in PROXIES_LIST:
        try:
            proxies = {"http": proxy, "https": proxy} if proxy else None
            proxy_log = proxy if proxy else "Direct Connection"
            print(f"Đang thử kết nối qua: {proxy_log}...")
            
            response = requests.get(
                API_URL, 
                headers=headers, 
                proxies=proxies,
                impersonate="chrome120", 
                timeout=12
            )
            if response.status_code == 200:
                print("-> Kết nối API thành công!")
                return response.json().get("data", [])
        except Exception as err:
            print(f"-> Thất bại ({err}), thử phương án tiếp theo...")
            continue
            
    raise Exception("Tất cả kết nối IP/Proxy đều bị từ chối (403/Timeout).")

def generate_m3u():
    data = fetch_data_with_fallback()
    m3u_content = "#EXTM3U\n\n"
    count = 0
    
    for match in data:
        if not match.get("OBS_stream_key"):
            continue
            
        stream_info = match["OBS_stream_key"][0]
        stream_key = stream_info.get("stream_key")
        if not stream_key:
            continue

        left_logo_id = match.get("left_club", {}).get("avatar", {}).get("id", "")
        logo_url = f"{IMAGE_BASE}{left_logo_id}" if left_logo_id else ""
        left_name = match.get("left_club", {}).get("name", "")
        right_name = match.get("right_club", {}).get("name", "")
        match_name = f"{left_name} vs {right_name}"
        
        group_title = get_group_title(match.get("competition", {}).get("name", ""))
        
        commentator = "Unknown"
        if stream_info.get("commentator") and stream_info["commentator"].get("name"):
            commentator = stream_info["commentator"]["name"]

        dt = datetime.strptime(match["time"], "%Y-%m-%dT%H:%M:%S")
        time_str = dt.strftime("%H:%M %d/%m")
        status_icon = "🟢 " if match.get("time_type") == "truc_tiep" else ""

        m3u_content += f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{group_title}" , {status_icon}{time_str} ⚽ {match_name} ({commentator}) [hls]\n'
        m3u_content += f'{STREAM_HLS_BASE}{stream_key}/index.m3u8\n\n'
        
        m3u_content += f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{group_title}" , {status_icon}{time_str} ⚽ {match_name} ({commentator}) [flv]\n'
        m3u_content += f'{STREAM_FLV_BASE}{stream_key}.flv\n\n'
        count += 1
        
    with open("s8tv.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Đã xuất thành công file s8tv.m3u với {count} luồng.")

if __name__ == "__main__":
    try:
        generate_m3u()
    except Exception as e:
        print(f"Lỗi khi chạy script: {e}", file=sys.stderr)
        sys.exit(1)
        
