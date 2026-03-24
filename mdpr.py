from bs4 import BeautifulSoup
import requests
import os
from urllib.parse import urlparse
import time

TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_THREAD_ID = os.environ.get("TELEGRAM_THREAD_ID")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# NEW: provide NEWS_ID, e.g. 4750240
NEWS_ID = os.environ.get("NEWS_ID")


def remove_all_params(url):
    parsed = urlparse(url)
    return parsed._replace(query="quality=100").geturl()


def get_first_photo_id_from_news():
    """
    Fetch https://mdpr.jp/music/{NEWS_ID}
    Find first <a class="c-image__image" href="/photo/detail/XXXXX">
    Return XXXXX
    """
    headers = {"User-Agent": "curl/8.5.0"}
    news_url = f"https://mdpr.jp/music/{NEWS_ID}"

    html = requests.get(news_url, headers=headers, timeout=30).text
    soup = BeautifulSoup(html, "lxml")

    a_tag = soup.find("a", class_="c-image__image")
    if not a_tag or not a_tag.get("href"):
        raise RuntimeError("First photo link not found on news page")

    # /photo/detail/19835587 → 19835587
    first_photo_id = a_tag["href"].rstrip("/").split("/")[-1]
    return first_photo_id


def parse_html(first_photo_id):
    headers = {"User-Agent": "curl/8.5.0"}
    photo_url = "https://mdpr.jp/photo/detail/" + first_photo_id

    photos_html = requests.get(photo_url, headers=headers, timeout=30).text
    with open("photos.html", "w", encoding="utf-8") as f:
        f.write(photos_html)

    soup = BeautifulSoup(photos_html, "lxml")
    picture_url_list = []

    # Main image block
    body = soup.find("div", class_="pg-photo__body")
    if body:
        for img in body.find_all("img"):
            img_src = img.get("src", "")
            if img_src and "protect" not in img_src:
                picture_url_list.append(remove_all_params(img_src))

    # Web image list
    web_list = soup.find("ol", class_="pg-photo__webImageList")
    if web_list:
        for img in web_list.find_all("img"):
            img_src = img.get("src", "")
            if img_src and "protect" not in img_src:
                picture_url_list.append(remove_all_params(img_src))

    print("Total images:", len(picture_url_list))
    return picture_url_list, first_photo_id


def send_telegram_photo(caption, img_url):
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "photo": img_url,
                "caption": caption,
            }
            if TELEGRAM_THREAD_ID:
                payload["message_thread_id"] = TELEGRAM_THREAD_ID

            resp = requests.post(url, json=payload)
            if "error_code" not in resp.json():
                time.sleep(5)
                return
        except Exception as e:
            print(e)
            time.sleep(5)


def send_telegram_file_link(caption, file_link):
    max_retries = 5
    for _ in range(max_retries):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
                "document": file_link,
                "parse_mode": "HTML",
            }
            if TELEGRAM_THREAD_ID:
                payload["message_thread_id"] = TELEGRAM_THREAD_ID

            resp = requests.post(url, data=payload, timeout=60)
            if "error_code" not in resp.json():
                return True
            else:
                print("sendDocument error:", resp.json())
        except Exception as e:
            print(e)
            time.sleep(20)
    return False


def send_telegram_message(caption):
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": caption,
                "parse_mode": "HTML",
            }
            if TELEGRAM_THREAD_ID:
                payload["message_thread_id"] = TELEGRAM_THREAD_ID

            resp = requests.post(url, data=payload)
            if "error_code" not in resp.json():
                time.sleep(5)
                return
            else:
                print(resp.json())
                return
        except Exception as e:
            print(e)
            time.sleep(5)


# =========================
# MAIN FLOW
# =========================

first_photo_id = get_first_photo_id_from_news()
picture_url_list, first_photo_id = parse_html(first_photo_id)

send_telegram_message("https://mdpr.jp/photo/detail/" + first_photo_id)

for i, picture_url in enumerate(picture_url_list):
    send_telegram_file_link(
        f"{i + 1}/{len(picture_url_list)}",
        picture_url,
    )
