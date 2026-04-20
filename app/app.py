from flask import Flask, render_template, request
import requests
from datetime import date
from functools import lru_cache

app = Flask(__name__)

SEASON = "2026"

# ==================== PARK FACTORS (ajustement pour le pitcher) ====================
PARK_FACTORS = {
    "Coors Field": -1,           # très hitter-friendly
    "Great American Ball Park": -0.5,
    "Yankee Stadium": -0.5,
    "Fenway Park": -0.5,
    "Oracle Park": 1,            # très pitcher-friendly
    "Dodger Stadium": 1,
    "T-Mobile Park": 1,
    "PETCO Park": 1,
    "Nationals Park": 0.5,
    "Progressive Field": 0.5,
    "Angel Stadium": 0.5,
    "Busch Stadium": 0.5,
    # les autres stades = 0 (neutre)
}

@lru_cache(maxsize=1)
def get_standings():
    """Récupère le win% de chaque équipe (une seule fois par session)"""
    url = f"https://statsapi.mlb.com/api/v1/standings?season={SEASON}&leagueId=103,104"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        standings = {}
        for record in data.get("records", []):
            for team in record.get("teamRecords", []):
                team_id = team["team"]["id"]
                pct = float(team["leagueRecord"]["pct"])
                standings[team_id] = pct
        return standings
    except:
        return {}

def get_pitcher_stats(pitcher_id):
    """Récupère les stats saison 2026 du pitcher"""
    if not pitcher_id:
        return {"era": "—", "record": "—", "whip": "—", "k9": "—"}
    
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats"
    params = {"stats": "season", "group": "pitching", "season": SEASON}
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data.get("stats") and data["stats"][0].get("splits"):
            stat = data["stats"][0]["splits"][0]["stat"]
            ip = stat.get("inningsPitched", 0)
            so = stat.get("strikeOuts", 0)
            k9 = round(so / ip * 9, 1) if ip > 0 else 0.0
            
            return {
                "era": stat.get("era", "—"),
                "record": f"{stat.get('wins',0)}-{stat.get('losses',0)}",
                "whip": stat.get("whip", "—"),
                "k9": k9
            }
    except:
        pass
    return {"era": "—", "record": "—", "whip": "—", "k9": "—"}

def get_matchup_grade(era_str, venue_name, opponent_win_pct=None):
    """Calcule la note A/B/C/D + commentaire"""
    if era_str == "—" or not era_str.replace(".", "").replace("-", "").isdigit():
        return "C", "Stats non disponibles"
    
    era = float(era_str)
    
    # Note de base
    if era <= 3.00: grade = "A"
    elif era <= 3.75: grade = "B"
    elif era <= 4.75: grade = "C"
    else: grade = "D"
    
    adjustment = 0
    comments = []
    
    # Stade
    park_adj = PARK_FACTORS.get(venue_name, 0)
    if park_adj < 0:
        adjustment -= 1
        comments.append("🏟️ Stade hitter-friendly")
    elif park_adj > 0:
        adjustment += 1
        comments.append("🏟️ Stade pitcher-friendly")
    else:
        comments.append("🏟️ Stade neutre")
    
    # Équipe adverse
    if opponent_win_pct:
        if opponent_win_pct > 0.55:
            adjustment -= 1
            comments.append("⚔️ Adversaire fort")
        elif opponent_win_pct < 0.45:
            adjustment += 1
            comments.append("⚔️ Adversaire faible")
        else:
            comments.append("⚔️ Adversaire moyen")
    
    # Application de l'ajustement
    grade_num = ord(grade) - ord("A")          # A=0, B=1, ...
    grade_num = max(0, min(3, grade_num - adjustment))  # +facile → meilleure note
    final_grade = chr(ord("A") + grade_num)
    
    return final_grade, " / ".join(comments)

@app.route("/")
def index():
    selected_date = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    standings = get_standings()
    
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "date": selected_date,
        "hydrate": "probablePitcher,venue"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except:
        data = {"dates": []}
    
    games = []
    if data.get("dates") and len(data["dates"]) > 0:
        for game in data["dates"][0]["games"]:
            away = game["teams"]["away"]
            home = game["teams"]["home"]
            venue_name = game.get("venue", {}).get("name", "—")
            
            # Away pitcher
            away_p = away.get("probablePitcher", {})
            away_id = away_p.get("id")
            away_name = away_p.get("fullName", "TBD")
            away_stats = get_pitcher_stats(away_id)
            away_opp_winpct = standings.get(home["team"]["id"])
            away_grade, away_note = get_matchup_grade(away_stats["era"], venue_name, away_opp_winpct)
            
            # Home pitcher
            home_p = home.get("probablePitcher", {})
            home_id = home_p.get("id")
            home_name = home_p.get("fullName", "TBD")
            home_stats = get_pitcher_stats(home_id)
            home_opp_winpct = standings.get(away["team"]["id"])
            home_grade, home_note = get_matchup_grade(home_stats["era"], venue_name, home_opp_winpct)
            
            games.append({
                "time": game["gameDate"][11:16] + " UTC",
                "away_team": away["team"]["name"],
                "home_team": home["team"]["name"],
                "away_pitcher": {
                    "name": away_name,
                    "stats": away_stats,
                    "grade": away_grade,
                    "note": away_note
                },
                "home_pitcher": {
                    "name": home_name,
                    "stats": home_stats,
                    "grade": home_grade,
                    "note": home_note
                },
                "venue": venue_name
            })
    
    return render_template("index.html", games=games, selected_date=selected_date)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
