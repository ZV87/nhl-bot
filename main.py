import os
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import pytz

# -----------------------------
# CONFIG
# -----------------------------
BOT_ID = "aab9ec997e5b8adfa86525bc30"

NHL_API = "https://statsapi.web.nhl.com/api/v1"
NEWS_API = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news"

FAV_TEAM = "Montreal Canadiens"
FAV_ID = 8  # Habs team ID

# -----------------------------
# GLOBALS
# -----------------------------
ALERTS_ENABLED = True  # Master toggle for all alerts

last_habs_goals = {
    "home": 0,
    "away": 0
}

# -----------------------------
# FLASK APP
# -----------------------------
app = Flask(__name__)


# -----------------------------
# SEND MESSAGE TO GROUPME
# -----------------------------
def send(msg):
    requests.post(
        "https://api.groupme.com/v3/bots/post",
        json={"bot_id": BOT_ID, "text": msg},
    )


# -----------------------------
# BASIC NHL FUNCTIONS
# -----------------------------
def get_scores():
    r = requests.get(f"{NHL_API}/schedule")
    data = r.json().get("dates", [])
    if not data:
        return "No games today."

    out = "Today's NHL Scores:\n"
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

    out = "NHL Standings:\n"
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
# LIVE HABS GAME FUNCTIONS
# -----------------------------
def get_live_habs_game():
    r = requests.get(f"{NHL_API}/schedule?teamId=8&expand=schedule.linescore")
    data = r.json()

    if not data.get("dates"):
        return None

    game = data["dates"][0]["games"][0]
    if game["status"]["detailedState"] != "In Progress":
        return None

    return game


def get_goal_details(game):
    game_id = game["gamePk"]
    pbp = requests.get(f"{NHL_API}/game/{game_id}/feed/live").json()

    scoring = pbp["liveData"]["plays"]["scoringPlays"]
    plays = pbp["liveData"]["plays"]["allPlays"]

    details = []

    for idx in scoring:
        p = plays[idx]
