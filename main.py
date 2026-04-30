from flask import Flask, request, Response, jsonify
import yt_dlp
import requests
import os

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
        # プレイリスト全体を強制的に取得するための設定
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # 1. 最優先: manifest_url (これが master.m3u8 に直結します)
            master_url = info.get('manifest_url') or info.get('url')
            
            # 2. formatsの中から 'hls' かつ 'master' という文字列を含むものを再検索
            formats = info.get('formats', [])
            all_m3u8 = [f['url'] for f in formats if 'm3u8' in f.get('url', '').lower()]
            
            # 特定のパターン (master.m3u8) を含むものを優先抽出
            best_master = next((u for u in all_m3u8 if 'master.m3u8' in u), master_url)

            return jsonify({
                "title": info.get('title'),
                "master_url": best_master,
                "all_m3u8_variants": all_m3u8
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
