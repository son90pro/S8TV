import json
import re
import sys
from datetime import datetime
import requests

API_TARGET = "https://s8tvkc.top/wp-json/s8-live/v1/fixtures"
WORKER_URL = f"https://vsc-proxy.sonnguyen90pro.workers.dev/?url={API_TARGET}"

STREAM_HLS_BASE = "https://hls.lauthaitv.cc/live/"
STREAM_FLV_BASE = "https://flv.lauthaitv.cc/live/"

IMAGE_BASE = "https://s8tvkc.top/wp-json/s8-image/"
DEFAULT_LOGO = "https://s8tvkc.top/wp-content/uploads/2026/04/cropped-favjcon-s8tv-192x192.webp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://s8tvkc.top/"
}

UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

def find_uuid_in_dict(data):
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str) and UUID_PATTERN.match(v.strip()):
                return v.strip()
            res = find_uuid_in_dict(v)
            if res:
                return res
    elif isinstance(data, list):
        for item in data:
            res = find_uuid_in_dict(item)
            if res:
                return res
    return None

def extract_club_logo(match):
    left_club = match.get("left_club") or {}
    
    # In trực tiếp và ép flush để hiện ngay trên log GitHub Actions
    print(f"\n--- DEBUG MATCH KEYS: {list(match.keys())} ---", flush=True)
    print("--- DEBUG LEFT_CLUB JSON ---", flush=True)
    print(json.dumps(left_club, ensure_ascii=False, indent=2), flush=True)
    print("----------------------------\n", flush=True)

    uuid_found = find_uuid_in_dict(left_club)
    if uuid_found:
        return f"{IMAGE_BASE}{uuid_found}"

    return DEFAULT_LOGO

def generate_m3u():
    print(f"Đang gọi API thông qua Cloudflare Worker: {WORKER_URL}", flush=True)
    response = requests.get(WORKER_URL, headers=HEADERS, timeout=15)
    response.raise_for_status() 
    
    res_json = response.json()
    
    if isinstance(res_json, dict):
        data = res_json.get("data", []) or res_json.get("fixtures", []) or res_json.get("response", [])
        if not data and "id" in res_json:
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

        logo_url = extract_club_logo(match)
        
        left_name = match.get("left_club", {}).get("name", "")
        right_name = match.get("right_club", {}).get("name", "")
        match_name = f"{left_name} vs {right_name}"
        
        group_title = "S8 TV"
        
        commentator = "Unknown"
        comm = stream_info.get("commentator")
        if isinstance(comm, dict):
            commentator = comm.get("name", "Unknown")
        elif isinstance(comm, str):
            commentator = comm

        time_val = match.get("time", "")
        try:
            dt = datetime.strptime(time_val, "%Y-%m-%dT%H:%M:%S")
            time_str = dt.strftime("%H:%M %d/%m")
        except Exception:
            time_str = time_val[:16] if time_val else ""
            
        is_live = match.get("time_type") == "truc_tiep" or match.get("status_code") == "LIVE"
        status_icon = "🟢 " if is_live else ""

        m3u_content += f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{group_title}" , {status_icon}{time_str} ⚽ {match_name} ({commentator}) [hls]\n'
        m3u_content += f'{STREAM_HLS_BASE}{stream_key}/index.m3u8\n\n'
        
        m3u_content += f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{group_title}" , {status_icon}{time_str} ⚽ {match_name} ({commentator}) [flv]\n'
        m3u_content += f'{STREAM_FLV_BASE}{stream_key}.flv\n\n'
        count += 1
        
    with open("s8tv.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Đã xuất thành công file s8tv.m3u với {count} luồng.", flush=True)

if __name__ == "__main__":
    try:
        generate_m3u()
    except Exception as e:
        print(f"Lỗi khi chạy script: {e}", file=sys.stderr)
        sys.exit(1)
        
