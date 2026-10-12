import json
import sys
from datetime import datetime
import requests

# Đường dẫn API chuẩn vừa bắt được từ mã nguồn S8TV
API_TARGET = "https://s8tvkc.top/wp-json/s8-live/v1/fixtures"
WORKER_URL = f"https://vsc-proxy.sonnguyen90pro.workers.dev/?url={API_TARGET}"

IMAGE_BASE = "https://s8tvkc.top/wp-json/s8-image/"
STREAM_HLS_BASE = "https://hls.lauthaitv.cc/live/"
STREAM_FLV_BASE = "https://flv.lauthaitv.cc/live/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://s8tvkc.top/"
}

def get_group_title(competition_name):
    if not competition_name:
        return "Bóng đá"
    name_lower = competition_name.lower()
    if any(kw in name_lower for kw in ["volleyball", "bóng chuyền"]): return "Bóng chuyền"
    if any(kw in name_lower for kw in ["basketball", "bóng rổ", "nba"]): return "Bóng rổ"
    if any(kw in name_lower for kw in ["tennis", "quần vợt"]): return "Tennis"
    return "Bóng đá"

def generate_m3u():
    print(f"Đang gọi API thông qua Cloudflare Worker: {WORKER_URL}")
    response = requests.get(WORKER_URL, headers=HEADERS, timeout=15)
    response.raise_for_status() 
    
    res_json = response.json()
    
    # Hỗ trợ lấy dữ liệu linh hoạt theo cấu trúc JSON mới
    if isinstance(res_json, dict):
        data = res_json.get("data", []) or res_json.get("fixtures", []) or res_json.get("response", [])
        if not data and "id" in res_json: # Trường hợp trả về 1 object trực tiếp
            data = [res_json]
    elif isinstance(res_json, list):
        data = res_json
    else:
        data = []

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

        time_val = match.get("time", "")
        try:
            dt = datetime.strptime(time_val, "%Y-%m-%dT%H:%M:%S")
            time_str = dt.strftime("%H:%M %d/%m")
        except Exception:
            time_str = time_val[:16] if time_val else ""
            
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
        
