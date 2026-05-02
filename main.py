from flask import Flask, request, Response, jsonify
import yt_dlp
import requests
import os
import re
from urllib.parse import urljoin, urlparse

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
            raw_url = info.get('manifest_url') or info.get('url')
            
            # ホスト名を iv-h に置換し、master.m3u8 に書き換える
            final_url = re.sub(r'https://[a-z0-9-]+.phncdn.com', 'https://iv-h.phncdn.com', raw_url)
            if '?' in final_url:
                base_path, query = final_url.split('?', 1)
                if not base_path.endswith('master.m3u8'):
                    base_path = re.sub(r'/[^/]+\.m3u8$', '/master.m3u8', base_path)
                final_url = f"{base_path}?{query}"
            
            # ブラウザで直接開くための proxy_video 経由のURLを生成
            # (Flaskサーバーのホスト名に合わせて適宜変更してください)
            proxy_ready_url = f"/proxy_video?stream_url={final_url}"

            return jsonify({
                "title": info.get('title'),
                "target_url": final_url,
                "proxy_url": proxy_ready_url,
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
    }

    req = requests.get(stream_url, proxies=proxies, headers=headers, verify=False, timeout=15)
    
    # m3u8ファイルの場合、中身のURLをすべてプロキシ経由に書き換える
    if "application/vnd.apple.mpegurl" in req.headers.get('Content-Type', '') or stream_url.split('?')[0].endswith('.m3u8'):
        content = req.text
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('#') or not line.strip():
                new_lines.append(line)
            else:
                # 相対パスや絶対パスをフルURLに変換し、さらにこの proxy_video を通すように書き換え
                full_url = urljoin(stream_url, line.strip())
                new_lines.append(f"/proxy_video?stream_url={full_url}")
        
        return Response('\n'.join(new_lines), content_type="application/vnd.apple.mpegurl")

    # 動画セグメント（.ts）などのバイナリデータはそのまま流す
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    response_headers = [(name, value) for (name, value) in req.raw.headers.items() if name.lower() not in excluded_headers]

    return Response(req.content, status=req.status_code, content_type=req.headers.get('Content-Type'), headers=response_headers)

if __name__ == "__main__":
    app.run(port=5000)
