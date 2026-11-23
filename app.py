"""AI Yo Music Flask application; safe for stateless Vercel Functions."""
import os
import uuid
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

GENRES = {"lofi", "pop", "rock", "electronic", "cinematic", "hiphop", "acoustic"}
MOODS = {"relaxing", "energetic", "dreamy", "hopeful", "dark", "focus"}
DURATIONS = {"30", "60", "120"}
MOCK_AUDIO_URL = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
TIMEOUT = (5, 25)


def _error(message, status=400, code="invalid_request"):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status


def _api_headers():
    return {"Authorization": f"Bearer {os.environ.get('MUSIC_API_KEY', '')}", "Content-Type": "application/json", "Accept": "application/json"}


def _safe_audio_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _request_error(exc):
    if isinstance(exc, requests.Timeout):
        return _error("音樂服務回應逾時，請稍後再試。", 504, "upstream_timeout")
    if isinstance(exc, requests.HTTPError):
        return _error("音樂服務目前無法完成請求，請稍後再試。", 502, "upstream_http_error")
    if isinstance(exc, requests.RequestException):
        return _error("目前無法連線至音樂服務，請稍後再試。", 502, "upstream_connection_error")
    if isinstance(exc, ValueError):
        return _error("音樂服務回傳的資料格式無法讀取，請稍後再試。", 502, "upstream_invalid_json")
    return _error("音樂生成遇到問題，請稍後再試。", 502, "upstream_error")


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ai-yo-music"})


@app.post("/api/generate")
def generate():
    if not request.is_json:
        return _error("請以 JSON 格式送出音樂設定。")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("請確認音樂設定內容正確。")
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return _error("先寫下一段音樂靈感再開始生成。")
    prompt = prompt.strip()
    if len(prompt) > 500:
        return _error("音樂描述請控制在 500 字以內。")
    genre, mood, duration = data.get("genre"), data.get("mood"), str(data.get("duration", ""))
    if genre not in GENRES or mood not in MOODS or duration not in DURATIONS:
        return _error("曲風、情緒或長度選項不正確，請重新選擇。")
    payload = {"prompt": prompt, "genre": genre, "mood": mood, "duration": int(duration)}
    mock = os.environ.get("MOCK_MODE", "false").lower() == "true" or not os.environ.get("MUSIC_API_KEY", "").strip()
    if mock:
        task_id = f"demo-{uuid.uuid4().hex[:12]}"
        return jsonify({"ok": True, "mode": "demo", "task_id": task_id, "status": "succeeded", "audio_url": MOCK_AUDIO_URL, "download_url": MOCK_AUDIO_URL, "summary": payload})

    base_url = os.environ.get("MUSIC_API_BASE_URL", "").strip().rstrip("/")
    if not base_url or not _safe_audio_url(base_url):
        return _error("音樂服務尚未完成設定，請聯絡網站管理員。", 503, "service_not_configured")
    try:
        response = requests.post(f"{base_url}/generate", headers=_api_headers(), json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        return _request_error(exc)
    if not isinstance(result, dict):
        return _error("音樂服務回傳的資料格式無法讀取，請稍後再試。", 502, "upstream_invalid_response")
    task_id = str(result.get("task_id") or result.get("id") or "")[:128]
    status = result.get("status", "processing")
    audio_url = result.get("audio_url") or result.get("url")
    if audio_url and not _safe_audio_url(audio_url):
        return _error("音樂服務回傳的音訊連結不安全，請稍後再試。", 502, "upstream_invalid_response")
    if status not in {"queued", "processing", "succeeded", "failed"}:
        status = "processing"
    if status == "succeeded" and not audio_url:
        status = "processing"
    return jsonify({"ok": True, "mode": "live", "task_id": task_id, "status": status, "audio_url": audio_url, "download_url": audio_url, "summary": payload})


@app.get("/api/status/<task_id>")
def status(task_id):
    if not task_id or len(task_id) > 128:
        return _error("任務編號格式不正確。")
    if task_id.startswith("demo-"):
        return jsonify({"ok": True, "task_id": task_id, "status": "succeeded", "audio_url": MOCK_AUDIO_URL})
    if not os.environ.get("MUSIC_API_KEY", "").strip():
        return _error("找不到這筆生成任務，請重新開始。", 404, "task_not_found")
    base_url = os.environ.get("MUSIC_API_BASE_URL", "").strip().rstrip("/")
    if not base_url or not _safe_audio_url(base_url):
        return _error("音樂服務尚未完成設定，請稍後再試。", 503, "service_not_configured")
    try:
        response = requests.get(f"{base_url}/status/{task_id}", headers=_api_headers(), timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        return _request_error(exc)
    if not isinstance(result, dict):
        return _error("音樂服務回傳的資料格式無法讀取，請稍後再試。", 502, "upstream_invalid_response")
    state = result.get("status")
    if state not in {"queued", "processing", "succeeded", "failed"}:
        return _error("音樂服務回傳了無法辨識的任務狀態。", 502, "upstream_invalid_response")
    audio_url = result.get("audio_url") or result.get("url")
    if audio_url and not _safe_audio_url(audio_url):
        return _error("音樂服務回傳的音訊連結不安全。", 502, "upstream_invalid_response")
    return jsonify({"ok": True, "task_id": task_id, "status": state, "audio_url": audio_url})


@app.errorhandler(413)
def too_large(_error):
    return _error("送出的內容太大，請縮短音樂描述後再試。", 413, "payload_too_large")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
