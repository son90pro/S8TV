import json
import requests
import sys
from datetime import datetime

API_URL = "https://s8tv002.com/api/fixtures/base"
IMAGE_BASE = "https://s8tvkc.top/wp-json/s8-image/"
STREAM_HLS_BASE = "https://hls.lauthaitv.cc/live/"
STREAM_FLV_BASE = "https://flv.lauthaitv.cc/live/"

def get_group_title(competition_name):
    name_lower = competition_name.lower()
    if any(kw in name_lower for kw in ["volleyball", "bóng chuyền"]): return "Bóng chuyền"
    if any(kw in name_lower for kw in ["basketball", "bóng rổ", "nba"]): return "Bóng rổ"
    if any(kw in name_lower for kw in ["tennis", "quần vợt"]): return "Tennis"
    return "Bóng đá"

def generate_m3u():
    headers = {"User-Agent": "Mozilla/5.0"}
    # Tăng timeout lên 15s và báo lỗi nếu HTTP status >= 400
    response = requests.get(API_URL, headers=headers, timeout=15)
    response.raise_for_status() 
    
    data = response.json().get("data", [])
    m3u_content = "#EXTM3U\n\n"
    count = 0
    
    for match in data:
        if not match.get("OBS_stream_key"):
            continue
            
        stream_info = match["OBS_stream_key"][0]
        stream_key = stream_info.get("stream_key")
        if not stream_key:
            continue

        left_logo_id = match["left_club"]["avatar"]["id"]
        logo_url = f"{IMAGE_BASE}{left_logo_id}"
        match_name = f"{match['left_club']['name']} vs {match['right_club']['name']}"
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
    print(f"Đã tạo thành công file s8tv.m3u với {count} luồng.")

if __name__ == "__main__":
    try:
        generate_m3u()
    except Exception as e:
        print(f"Lỗi khi chạy script: {e}", file=sys.stderr)
        sys.exit(1) # Bắn lỗi dừng GitHub Actions lập tức
