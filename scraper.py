import json
import sys
from datetime import datetime
import requests

# Đường dẫn API chuẩn của S8TV
API_TARGET = "https://s8tvkc.top/wp-json/s8-live/v1/fixtures"
WORKER_URL = f"https://vsc-proxy.sonnguyen90pro.workers.dev/?url={API_TARGET}"

STREAM_HLS_BASE = "https://hls.lauthaitv.cc/live/"
STREAM_FLV_BASE = "https://flv.lauthaitv.cc/live/"

# Endpoint ảnh logo của S8TV
IMAGE_BASE = "https://s8tvkc.top/wp-json/s8-image/"
DEFAULT_LOGO = "https://s8tvkc.top/wp-content/uploads/2026/04/cropped-favjcon-s8tv-192x192.webp"

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

def extract_club_logo(match):
    """Trích xuất chính xác ID hoặc URL logo CLB từ dữ liệu API S8TV"""
    left_club = match.get("left_club") or {}
    
    # 1. Kiểm tra nếu có URL ảnh trực tiếp dạng http
    for key in ["logo", "avatar", "logo_url", "url", "src"]:
        val = left_club.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
        elif isinstance(val, dict):
            u = val.get("url") or val.get("src")
            if isinstance(u, str) and u.startswith("http"):
                return u

    # 2. Tìm ID của ảnh trong left_club (logo_id, avatar_id, id, avatar)
    img_id = (
        left_club.get("logo_id") or 
        left_club.get("avatar_id") or 
        left_club.get("id")
    )
    
    if not img_id and isinstance(left_club.get("avatar"), (int, str)):
        img_id = left_club.get("avatar")
        
    if img_id and str(img_id).isdigit():
        return f"{IMAGE_BASE}{img_id}"

    # 3. Thử tìm logo ở cấp độ match trực tiếp (left_logo, left_club_logo)
    direct_id = match.get("left_logo") or match.get("left_club_logo") or match.get("left_logo_id")
    if direct_id and str(direct_id).isdigit():
        return f"{IMAGE_BASE}{direct_id}"

    # 4. Thử lấy logo giải đấu
    comp = match.get("competition") or {}
    comp_logo = comp.get("avatar") or comp.get("logo") or comp.get("id")
    if isinstance(comp_logo, dict):
        c_id = comp_logo.get("id") or comp_logo.get("avatar_id")
        if c_id:
            return f"{IMAGE_BASE}{c_id}"
    elif comp_logo and str(comp_logo).isdigit():
        return f"{IMAGE_BASE}{comp_logo}"

    return DEFAULT_LOGO

def generate_m3u():
    print(f"Đang gọi API thông qua Cloudflare Worker: {WORKER_URL}")
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
        
