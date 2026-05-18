import os
import json
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def scrape_xvideos(keyword, page):
    # Vercelのサーバーレス環境に対応したPlaywrightの起動オプション
    # サンドボックスをオフにしないとコンテナ内で起動に失敗します
    launch_options = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
    }

    url = f"https://www.xvideos.com/?k={keyword}&p={page}"

    with sync_playwright() as p:
        # Chromiumブラウザを起動
        browser = p.chromium.launch(**launch_options)
        
        # 実際のブラウザに見せかけるためのUser-Agentを設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page_ctx = context.new_page()
        
        try:
            # タイムアウトを45秒に設定（Vercelの制限対策）
            page_ctx.goto(url, timeout=45000, wait_until="domcontentloaded")
            html = page_ctx.content()
        except Exception as e:
            browser.close()
            return {"error": f"ページの読み込みに失敗しました: {str(e)}", "videos": []}
            
        browser.close()

    # BeautifulSoupによるHTML解析
    soup = BeautifulSoup(html, "html.parser")
    video_list = []
    
    # xvideosの動画要素（div.mozaique）を取得
    videos = soup.find_all("div", class_="mozaique")
    if not videos:
        # レイアウトが異なる場合のフォールバック
        videos = soup.find_all("div", class_="thumb-block")

    for video in videos:
        try:
            # タイトルとURLの抽出
            title_tag = video.find("p", class_="title")
            if not title_tag:
                title_tag = video.find("a", title=True)
                
            if title_tag:
                a_tag = title_tag.find("a") if title_tag.name == "p" else title_tag
                title = a_tag.get("title") or a_tag.text.strip()
                href = a_tag.get("href")
                video_url = f"https://www.xvideos.com{href}" if href.startswith("/") else href
                
                # 再生時間、閲覧数の抽出
                duration = "不明"
                metadata = video.find("span", class_="duration")
                if metadata:
                    duration = metadata.text.strip()

                video_list.append({
                    "title": title,
                    "url": video_url,
                    "duration": duration
                })
        except Exception:
            continue

    return {"videos": video_list, "count": len(video_list)}


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "running",
        "usage": "/search?k=キーワード&p=1"
    })


@app.route("/search", methods=["GET"])
def search():
    # クエリパラメータの取得
    keyword = request.args.get("k", default="", type=str)
    page = request.args.get("p", default=1, type=int)

    if not keyword:
        return jsonify({"error": "キーワード 'k' は必須です。"}), 400

    try:
        result = scrape_xvideos(keyword, page)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"サーバー内部エラー: {str(e)}"}), 500


# Vercel環境用のハンドラー指定
# Flaskオブジェクトをそのままエクスポートします
app = app
