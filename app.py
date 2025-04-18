from flask import Flask, request, redirect, session, jsonify
from supabase import create_client, Client
from flask_cors import CORS
import os
import requests

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = "supersecretkey"

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Discord OAuth config
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

@app.route("/login")
def login():
    # Redirect to Discord's OAuth2 authorization page
    return redirect(
        f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"
    )

@app.route("/callback")
def callback():
    # Handle the OAuth2 callback and fetch the user's Discord info
    code = request.args.get("code")
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify'
    }

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    # Exchange the authorization code for an access token
    token_res = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    # Fetch the user's Discord information
    user_res = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    user = user_res.json()
    user_id = user["id"]
    username = f"{user['username']}#{user['discriminator']}"

    # Check if user exists in Supabase, and increment the login count or create a new entry
    existing = supabase.table("logins").select("*").eq("discord_id", user_id).execute()
    if existing.data:
        # If user exists, update the count
        supabase.table("logins").update({"count": existing.data[0]["count"] + 1}).eq("discord_id", user_id).execute()
    else:
        # If user does not exist, insert a new record
        supabase.table("logins").insert({"discord_id": user_id, "username": username, "count": 1}).execute()

    # Save the user ID in the session
    session["user_id"] = user_id
    return redirect("https://your-vercel-site.vercel.app")  # Replace with your actual frontend URL

@app.route("/me")
def me():
    # Fetch the logged-in user's information from Supabase
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    result = supabase.table("logins").select("*").eq("discord_id", user_id).single().execute()
    return jsonify(result.data)

@app.route("/total_logins")
def total_logins():
    # Fetch the total login count from all users
    result = supabase.table("logins").select("count").execute()
    total = sum([r["count"] for r in result.data]) if result.data else 0
    return jsonify({"total_logins": total})

if __name__ == "__main__":
    app.run(debug=True)
