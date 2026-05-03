import os
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import pytz

BOT_ID = "aab9ec997e5b8adfa86525bc30"

app = Flask(__name__)

NHL_API = "https://statsapi.web.nhl.com/api/v1"
ODDS_API = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds"
NEWS_API = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news"

FAV_TEAM = "Montreal Canadiens"
FAV_ID = 8  # Habs team ID


# -----------------------------
# GroupMe Send Message
# -----------------------------
def send(msg):
    requests.post(
        "https://api.groupme.com/v3/bots/post",
        json={"bot_id": BOT_ID, "text": msg},
    )


# -----------------------------
# NHL Data Functions
# -----------------------------
def get_scores():
    r = requests.get(f"{NHL_API}/schedule")
    data = r.json()["dates"]
    if not data:
        return "No games today."

    out = "🏒 Today's NHL Scores\n"
    for game in data[0]["games"]:
        home = game["teams"]["home"]["team"]["name"]
        away = game["teams"]["away"]["team"]["name"]
        status = game["status"]["detailedState"]

        if "linescore" in game:
            h = game["linescore"]["teams"]["home"]["goals"]
            a = game["linescore"]["teams"]["away"]["goals"]
            out += f"{away} {a} - {home} {h} ({status})\n"
        else:
            out += f"{away} @ {home} ({status})\n"

    return out


def get_standings():
    r = requests.get(f"{NHL_API}/standings")
    data = r.json()["records"]

    out = "🏆 NHL Standings\n"
    for division in data:
        out += f"\n{division['division']['name']}:\n"
        for team in division["teamRecords"]:
            name = team["team"]["name"]
            pts = team["points"]
            out += f"{name}: {pts} pts\n"

    return out


def get_team_stats(team):
    r = requests.get(f"{NHL_API}/teams")
    teams = r.json()["teams"]

    tid = None
    for t in teams:
        if team.lower() in t["name"].lower():
            tid = t["id"]

    if not tid:
        return "Team not found."

    r = requests.get(f"{NHL_API}/teams/{tid}/stats")
    stats = r.json()["stats"][0]["splits"][0]["stat"]

    return (
        f"{team} Stats:\n"
        f"Wins: {stats['wins']}\n"
        f"Losses: {stats['losses']}\n"
        f"Points: {stats['pts']}"
    )


# -----------------------------
# Flask Webhook for GroupMe
# -----------------------------
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data or "text" not in data:
        return "OK", 200

    msg = data["text"].lower()

    if msg == "!scores":
        send(get_scores())

    elif msg == "!standings":
        send(get_standings())

    elif msg.startswith("!team "):
        team = msg.replace("!team ", "")
        send(get_team_stats(team))

    elif msg == "!help":
        send("Commands:\n!scores\n!standings\n!team <name>\n!help")

    return "OK", 200


# -----------------------------
# Run the Flask App
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))