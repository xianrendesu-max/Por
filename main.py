from fastapi import FastAPI, Query, HTTPException
from pornhub_api import PornhubApi
import yt_dlp
import os
from fastapi.responses import JSONResponse

app = FastAPI()
api = PornhubApi()

# --- FastAPIによる検索APIセクション ---

@app.get("/search")
def search_videos(
    q: str = Query(..., description="検索キーワード"),
    limit: int = Query(10, description="取得件数"),
    page: int = Query(1, description="ページ番号")
):
    # 動画を検索（並び順や期間などのオプションも設定可能）
    # ordering="mostviewed", period="weekly" など
    results = api.search.search_videos(
        q, 
        page=page
    )
    
    video_list = []
    # 検索結果から必要な情報だけを抽出
    for i, video in enumerate(results.videos):
        if i >= limit:
            break
        video_list.append({
            "title": video.title,
            "video_id": video.video_id,
            "url": video.url,
            "duration": video.duration,
            "views": video.views,
            "rating": video.rating,
            "thumbnail": video.default_thumb,
        })

    return {
        "keyword": q,
        "count": len(video_list),
        "results": video_list
    }

# --- yt-dlpによる情報取得・ストリームAPIセクション ---

@app.get("/")
def index():
    return {
        "status": "online",
        "message": "yt-dlp JSON API for Pornhub is running",
        "proxy": "active"
    }

@app.get("/get_info")
def get_info(url: str = Query(..., alias="url")):
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
            info = ydl.extract_info(url, download=False)
            
            # 抽出した情報をJSONとして返却
            return info
            
    except Exception as e:
        # エラー発生時の詳細を返却
        raise HTTPException(status_code=500, detail={
            "error": "Failed to extract video information",
            "details": str(e)
        })

@app.get("/api/v1/stream/{video_id}")
def get_stream_info(video_id: str):
    video_url = f"https://www.pornhub.com/view_video.php?viewkey={video_id}"
    proxy_url = "http://ytproxy-siawaseok.duckdns.org:3007"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'proxy': proxy_url,
        'nocheckcertificate': True,
        'format': 'best',
        'referer': 'https://www.pornhub.com/',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # HLSストリームURL、タイトル、サムネイルを抽出して返却
            return {
                "title": info.get("title"),
                "url": info.get("url"), # HLSストリームURL
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader")
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "Failed to extract stream information",
            "details": str(e)
        })

# Vercelデプロイ用: ハンドラとしてappを公開
# ローカル実行時のためのブロック
if __name__ == "__main__":
    import uvicorn
    # Renderなどの環境変数PORTに対応
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
