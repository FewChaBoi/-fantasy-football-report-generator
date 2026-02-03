"""Yahoo Fantasy API client for web application."""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime

from auth import YahooTokens


# NFL Game IDs by year
NFL_GAME_IDS = {
    2025: 461, 2024: 449, 2023: 423, 2022: 414, 2021: 406,
    2020: 399, 2019: 390, 2018: 380, 2017: 371, 2016: 359,
    2015: 348, 2014: 331, 2013: 314, 2012: 273, 2011: 257,
    2010: 242, 2009: 222, 2008: 199, 2007: 175, 2006: 153,
}


def get_year_from_game_id(game_id: int) -> Optional[int]:
    """Get year from game ID."""
    for year, gid in NFL_GAME_IDS.items():
        if gid == game_id:
            return year
    return None


class YahooFantasyAPI:
    """Yahoo Fantasy API client."""

    BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"

    def __init__(self, tokens: YahooTokens):
        self.tokens = tokens

    def _get_headers(self) -> dict:
        """Get request headers with auth."""
        return {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "Content-Type": "application/json",
        }

    async def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to Yahoo API."""
        url = f"{self.BASE_URL}/{endpoint}"
        if params is None:
            params = {}
        params["format"] = "json"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_user_leagues(self, year: int) -> List[str]:
        """Get user's league IDs for a specific year."""
        game_id = NFL_GAME_IDS.get(year)
        if not game_id:
            return []

        try:
            data = await self._get(f"users;use_login=1/games;game_keys={game_id}/leagues")
            leagues = []

            # Parse the nested structure
            users = data.get("fantasy_content", {}).get("users", {})
            user = users.get("0", {}).get("user", [])

            if len(user) > 1:
                games = user[1].get("games", {})
                game = games.get("0", {}).get("game", [])

                if len(game) > 1:
                    leagues_data = game[1].get("leagues", {})
                    for key, val in leagues_data.items():
                        if key != "count" and isinstance(val, dict):
                            league = val.get("league", [[]])[0]
                            for item in league:
                                if isinstance(item, dict) and "league_key" in item:
                                    leagues.append(item["league_key"])

            return leagues
        except Exception as e:
            print(f"Error getting leagues for {year}: {e}")
            return []

    async def get_league_settings(self, league_key: str) -> dict:
        """Get league settings."""
        data = await self._get(f"league/{league_key}/settings")
        settings = data.get("fantasy_content", {}).get("league", [[]])[0]

        result = {}
        for item in settings:
            if isinstance(item, dict):
                result.update(item)

        return result

    async def get_league_teams(self, league_key: str) -> dict:
        """Get teams in a league."""
        data = await self._get(f"league/{league_key}/teams")

        teams = {}
        league_data = data.get("fantasy_content", {}).get("league", [])

        if len(league_data) > 1:
            teams_data = league_data[1].get("teams", {})
            for key, val in teams_data.items():
                if key != "count" and isinstance(val, dict):
                    team = val.get("team", [[]])[0]
                    team_info = {}
                    for item in team:
                        if isinstance(item, dict):
                            if "team_key" in item:
                                team_info["team_key"] = item["team_key"]
                            elif "name" in item:
                                team_info["name"] = item["name"]
                            elif "managers" in item:
                                managers = item["managers"]
                                if managers:
                                    mgr = managers[0].get("manager", {})
                                    team_info["manager"] = mgr.get("nickname", "Unknown")

                    if "team_key" in team_info:
                        teams[team_info["team_key"]] = team_info

        return teams

    async def get_league_standings(self, league_key: str) -> List[dict]:
        """Get league standings."""
        data = await self._get(f"league/{league_key}/standings")

        standings = []
        league_data = data.get("fantasy_content", {}).get("league", [])

        if len(league_data) > 1:
            standings_data = league_data[1].get("standings", [[]])[0].get("teams", {})
            for key, val in standings_data.items():
                if key != "count" and isinstance(val, dict):
                    team = val.get("team", [])
                    team_info = {}

                    # Parse team info
                    if team and len(team) > 0:
                        for item in team[0]:
                            if isinstance(item, dict):
                                if "team_key" in item:
                                    team_info["team_key"] = item["team_key"]
                                elif "name" in item:
                                    team_info["name"] = item["name"]
                                elif "managers" in item:
                                    managers = item["managers"]
                                    if managers:
                                        mgr = managers[0].get("manager", {})
                                        team_info["manager"] = mgr.get("nickname", "Unknown")

                    # Parse standings info
                    if len(team) > 1:
                        standings_info = team[1].get("team_standings", {})
                        team_info["rank"] = int(standings_info.get("rank", 0))
                        team_info["points_for"] = float(standings_info.get("points_for", 0))
                        team_info["points_against"] = float(standings_info.get("points_against", 0))

                        outcomes = standings_info.get("outcome_totals", {})
                        team_info["wins"] = int(outcomes.get("wins", 0))
                        team_info["losses"] = int(outcomes.get("losses", 0))
                        team_info["ties"] = int(outcomes.get("ties", 0))

                    standings.append(team_info)

        return standings

    async def get_matchups(self, league_key: str, week: int) -> List[dict]:
        """Get matchups for a specific week."""
        try:
            data = await self._get(f"league/{league_key}/scoreboard;week={week}")

            matchups = []
            league_data = data.get("fantasy_content", {}).get("league", [])

            if len(league_data) > 1:
                scoreboard = league_data[1].get("scoreboard", {})
                matchups_data = scoreboard.get("0", {}).get("matchups", {})

                for key, val in matchups_data.items():
                    if key == "count" or not isinstance(val, dict):
                        continue

                    matchup = val.get("matchup", {})
                    teams_data = matchup.get("0", {}).get("teams", {})

                    t1_data = teams_data.get("0")
                    t2_data = teams_data.get("1")

                    if not t1_data or not t2_data:
                        continue

                    t1 = self._parse_team_matchup(t1_data)
                    t2 = self._parse_team_matchup(t2_data)

                    is_playoff = matchup.get("is_playoffs", "0") == "1"

                    matchups.append({
                        "week": week,
                        "team1": t1,
                        "team2": t2,
                        "is_playoff": is_playoff,
                    })

            return matchups
        except Exception:
            return []

    def _parse_team_matchup(self, team_data: dict) -> dict:
        """Parse team data from matchup."""
        info = {}
        team = team_data.get("team", [])

        if team and len(team) > 0:
            for item in team[0]:
                if isinstance(item, dict):
                    if "team_key" in item:
                        info["team_key"] = item["team_key"]
                    elif "name" in item:
                        info["name"] = item["name"]
                    elif "managers" in item:
                        managers = item["managers"]
                        if managers:
                            mgr = managers[0].get("manager", {})
                            info["manager"] = mgr.get("nickname", "Unknown")

        if len(team) > 1:
            info["points"] = float(team[1].get("team_points", {}).get("total", 0))

        return info

    async def get_transactions(self, league_key: str, tran_type: str, count: int = 100) -> List[dict]:
        """Get transactions of a specific type."""
        try:
            data = await self._get(
                f"league/{league_key}/transactions;types={tran_type};count={count}"
            )

            transactions = []
            league_data = data.get("fantasy_content", {}).get("league", [])

            if len(league_data) > 1:
                trans_data = league_data[1].get("transactions", {})

                for key, val in trans_data.items():
                    if key == "count" or not isinstance(val, dict):
                        continue

                    transaction = val.get("transaction", [])
                    if not transaction:
                        continue

                    txn_info = {}
                    for item in transaction[0]:
                        if isinstance(item, dict):
                            txn_info.update(item)

                    if len(transaction) > 1:
                        txn_info["players"] = transaction[1].get("players", {})

                    transactions.append(txn_info)

            return transactions
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []


async def discover_league_history(api: YahooFantasyAPI, initial_league_key: str) -> tuple:
    """
    Discover all historical seasons for a league.

    Returns:
        tuple: (list of (league_key, year) tuples, league_name)
    """
    # Parse initial league key
    parts = initial_league_key.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid league key format: {initial_league_key}")

    initial_game_id = int(parts[0])
    initial_year = get_year_from_game_id(initial_game_id)

    # Get league name
    try:
        settings = await api.get_league_settings(initial_league_key)
        league_name = settings.get("name", "Unknown League")
    except Exception:
        league_name = "Fantasy Football League"

    # Search for historical seasons
    found_leagues = []

    for year in sorted(NFL_GAME_IDS.keys(), reverse=True):
        try:
            league_ids = await api.get_user_leagues(year)

            for lid in league_ids:
                try:
                    settings = await api.get_league_settings(lid)
                    name = settings.get("name", "")

                    if name == league_name:
                        found_leagues.append((lid, year))
                        break
                except Exception:
                    continue
        except Exception:
            continue

    if not found_leagues:
        found_leagues = [(initial_league_key, initial_year)]

    return found_leagues, league_name
