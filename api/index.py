from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

# Vercel用にappをhandlerとして定義（慣習的なものですが、Flaskオブジェクトそのままでも動作します）
app.debug = True

# ルートディレクトリにアクセスした際の確認用
@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "message": "yt-dlp JSON API for Pornhub is running",
        "proxy": "active"
    })

@app.route('/get_info')
def get_info():
    # クエリパラメータから動画URLを取得
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    # 指定されたプロキシサーバー
    proxy_url = "http://ytproxy-siawaseok.duckdns.org:3007"

    # yt-dlpのオプション設定
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'proxy': proxy_url,
        'nocheckcertificate': True,
        'format': 'best', # 最良の画質を選択
        # Pornhubのブロックを回避するための偽装ヘッダー
        'referer': 'https://www.pornhub.com/',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 情報を抽出（download=Falseでメタデータのみ取得）
            info = ydl.extract_info(video_url, download=False)
            
            # 抽出した情報をJSONとして返却
            return jsonify(info)
            
    except Exception as e:
        # エラー発生時の詳細を返却
        return jsonify({
            "error": "Failed to extract video information",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    # Renderが指定するポート番号、または5000番で起動
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
