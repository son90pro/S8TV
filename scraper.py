import json
import sys
import requests
from datetime import datetime

# Đường dẫn Cloudflare Worker Proxy
WORKER_URL = "https://vsc-proxy.sonnguyen90pro.workers.dev/"

IMAGE_BASE = "https://s8tvkc.top/wp-json/s8-image/"
STREAM_HLS_BASE = "https://hls.lauthaitv.cc/live/"
STREAM_FLV_BASE = "https://flv.lauthaitv.cc/live/"

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
    response = requests.get(WORKER_URL, timeout=15)
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
