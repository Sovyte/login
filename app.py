import os
import requests
from flask import Flask, redirect, request, session, url_for, render_template
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
DISCORD_API_URL = "https://discord.com/api/v10"

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For secure sessions

# Home page
@app.route("/")
def home():
    return render_template("index.html")

# Login route → Discord OAuth2
@app.route("/login")
def login():
    return redirect(
        f"https://discord.com/oauth2/authorize?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code&scope=identify"
    )

# Callback from Discord
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided by Discord", 400

    # Exchange code for access token
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(f"{DISCORD_API_URL}/oauth2/token", data=data, headers=headers)
    if response.status_code != 200:
        return "Failed to get token from Discord", 500

    access_token = response.json().get("access_token")
    session["access_token"] = access_token
    return redirect(url_for("profile"))

# User profile
@app.route("/profile")
def profile():
    if "access_token" not in session:
        return redirect(url_for("home"))

    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    user_data = requests.get(f"{DISCORD_API_URL}/users/@me", headers=headers).json()

    avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png"
    return render_template("profile.html",
                           username=user_data["username"],
                           discriminator=user_data["discriminator"],
                           user_id=user_data["id"],
                           avatar_url=avatar_url)

# Optional: logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
