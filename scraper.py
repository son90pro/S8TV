import requests
import json
from datetime import datetime

API_URL = "https://s8tv002.com/api/fixtures/base"
IMAGE_PREFIX = "https://s8tvkc.top/wp-json/s8-image/"
BASE_HLS = "https://hls.lauthaitv.cc/live"
BASE_FLV = "https://flv.lauthaitv.cc/live"

def get_sport_info(fixture):
    tracker = fixture.get("sportscore_tracker_url") or ""
    slug = fixture.get("sportscore_slug") or ""
    comp_name = fixture.get("competition", {}).get("name", "").lower()
    
    if "volleyball" in tracker or "bong-chuyen" in slug:
        return "🏐", "Bóng chuyền"
    elif "basketball" in tracker or "bong-ro" in slug:
        return "🏀", "Bóng rổ"
    elif "table-tennis" in tracker or "bong-tan" in slug:
        return "🏓", "Bóng bàn"
    elif "badminton" in tracker or "cau-long" in slug:
        return "🏸", "Cầu lông"
    elif "highlight" in slug or "highlight" in comp_name:
        return "🎥", "Highlight"
    elif "esports" in tracker or "game" in comp_name:
        return "🎮", "Sports Games"
    else:
        return "⚽", "Bóng đá"

def build_m3u():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://s8tv002.com/",
        "Accept": "application/json"
    }
    
    try:
        res = requests.get(API_URL, headers=headers, timeout=25)
        res.raise_for_status()
        data = res.json().get("data", [])
    except Exception as e:
        print(f"Lỗi khi gọi API S8TV: {e}")
        raise e  # Dừng script và báo lỗi ngay tại bước Run Scraper

    channels = []

    for item in data:
        if not item.get("is_active", True):
            continue

        time_str = item.get("time", "")
        formatted_time = ""
        if time_str:
            try:
                dt = datetime.fromisoformat(time_str)
                formatted_time = dt.strftime("%H:%M %d/%m")
            except Exception:
                formatted_time = time_str

        left_club = item.get("left_club", {}).get("name", "Đội A")
        right_club = item.get("right_club", {}).get("name", "Đội B")
        
        obs_keys = item.get("OBS_stream_key", [])
        commentator_name = ""
        stream_key = ""
        if obs_keys and len(obs_keys) > 0:
            stream_key = obs_keys[0].get("stream_key", "")
            comm = obs_keys[0].get("commentator")
            if comm and comm.get("name"):
                commentator_name = f" ({comm['name'].strip()})"

        if not stream_key:
            continue

        logo_id = item.get("left_club", {}).get("avatar", {}).get("filename_disk") or \
                  item.get("left_club", {}).get("avatar", {}).get("id", "")
        
        if logo_id.startswith("http"):
            logo_url = logo_id
        elif logo_id:
            clean_id = logo_id.split('.')[0]
            logo_url = f"{IMAGE_PREFIX}{clean_id}"
        else:
            logo_url = ""

        time_type = item.get("time_type", "")
        status_icon = "🟢 " if time_type == "truc_tiep" else ("🟡 " if item.get("is_hot_match") else "")

        sport_icon, group_title = get_sport_info(item)
        title_base = f"{status_icon}{formatted_time} {sport_icon} {left_club} vs {right_club}{commentator_name}"

        channels.append({
            "group": group_title,
            "logo": logo_url,
            "title": f"{title_base} [hls]",
            "url": f"{BASE_HLS}/{stream_key}/index.m3u8"
        })
        
        channels.append({
            "group": group_title,
            "logo": logo_url,
            "title": f"{title_base} [flv]",
            "url": f"{BASE_FLV}/{stream_key}.flv"
        })

    order_priority = ["Bóng đá", "Bóng chuyền", "Bóng rổ", "Bóng bàn", "Cầu lông", "Sports Games", "Highlight"]
    channels.sort(key=lambda x: order_priority.index(x["group"]) if x["group"] in order_priority else 99)

    with open("s8tv.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")
        for ch in channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{ch["group"]}" , {ch["title"]}\n')
            f.write(f'{ch["url"]}\n\n')

    print(f"Đã tạo thành công file s8tv.m3u với {len(channels)} kênh.")

if __name__ == "__main__":
    build_m3u()
