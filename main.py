from flask import Flask, request, Response, jsonify
import yt_dlp
import requests
import os
import re

app = Flask(__name__)

# 指定されたプロキシ
PROXY_URL = "http://ytproxy-siawaseok.duckdns.org:3007"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'

@app.route('/get_info')
def get_info():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing url"}), 400

    ydl_opts = {
        'quiet': True,
        'proxy': PROXY_URL,
        'user_agent': USER_AGENT,
        'referer': 'https://www.pornhub.com/',
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # 元となるURLを取得
            raw_url = info.get('manifest_url') or info.get('url')
            
            # --- URLの強制変換ロジック（修正版） ---
            # 1. ホスト名を [任意].phncdn.com から iv-h.phncdn.com に置換（クエリは維持）
            final_url = re.sub(r'https://[a-z0-9-]+.phncdn.com', 'https://iv-h.phncdn.com', raw_url)
            
            # 2. ファイル名が index-... になっている場合、パス部分のみ master.m3u8 に書き換え
            if 'master.m3u8' not in final_url.split('?')[0]:
                # パス末尾の .m3u8 ファイル名を master.m3u8 に置換。? 以降のパラメータは保持。
                final_url = re.sub(r'/([^/]+)\.m3u8', '/master.m3u8', final_url, count=1)

            return jsonify({
                "title": info.get('title'),
                "target_url": final_url,
                "original_raw_url": raw_url
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/proxy_video')
def proxy_video():
    stream_url = request.args.get('stream_url')
    if not stream_url:
        return "Missing stream_url", 400

    proxies = {"http": PROXY_URL, "https": PROXY_URL}
    headers = {
        'User-Agent': USER_AGENT,
        'Referer': 'https://www.pornhub.com/',
        'Range': request.headers.get('Range', '')
    }

    req = requests.get(stream_url, proxies=proxies, headers=headers, stream=True, verify=False, timeout=15)
    
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    response_headers = [(name, value) for (name, value) in req.raw.headers.items() if name.lower() not in excluded_headers]

    def generate():
        for chunk in req.iter_content(chunk_size=65536):
            yield chunk

    return Response(generate(), status=req.status_code, content_type=req.headers.get('Content-Type'), headers=response_headers)

if __name__ == "__main__":
    app.run()
