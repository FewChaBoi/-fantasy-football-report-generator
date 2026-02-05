"""Report generation service."""

import asyncio
from pathlib import Path
from typing import List, Tuple, Any
from datetime import datetime
from io import BytesIO

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, HRFlowable
)

from yahoo_api import YahooFantasyAPI
from analysis import (
    head_to_head, scoring, wins, playoffs, games,
    luck, trades, waivers, consistency
)
from charts import create_h2h_heatmap, create_yearly_scoring_chart


def calculate_standings_from_matchups(matchups: List[dict], teams: dict, season: int) -> List[dict]:
    """Calculate standings from matchup data when API doesn't return standings info."""
    team_stats = {}

    # Initialize stats for all teams
    for tk, tv in teams.items():
        team_stats[tk] = {
            'team_key': tk,
            'name': tv.get('name', 'Unknown'),
            'manager': tv.get('manager', 'Unknown'),
            'wins': 0,
            'losses': 0,
            'ties': 0,
            'points_for': 0.0,
            'points_against': 0.0,
        }

    # Calculate stats from matchups (regular season only)
    for m in matchups:
        if m.get('season') != season:
            continue
        if m.get('is_playoff', False):
            continue

        t1_key = m.get('team1_id', '')
        t2_key = m.get('team2_id', '')
        s1 = m.get('score1', 0)
        s2 = m.get('score2', 0)

        if t1_key in team_stats:
            team_stats[t1_key]['points_for'] += s1
            team_stats[t1_key]['points_against'] += s2
            if s1 > s2:
                team_stats[t1_key]['wins'] += 1
            elif s1 < s2:
                team_stats[t1_key]['losses'] += 1
            else:
                team_stats[t1_key]['ties'] += 1

        if t2_key in team_stats:
            team_stats[t2_key]['points_for'] += s2
            team_stats[t2_key]['points_against'] += s1
            if s2 > s1:
                team_stats[t2_key]['wins'] += 1
            elif s2 < s1:
                team_stats[t2_key]['losses'] += 1
            else:
                team_stats[t2_key]['ties'] += 1

    # Convert to list and rank by wins (then points_for as tiebreaker)
    standings_list = list(team_stats.values())
    standings_list.sort(key=lambda x: (-x['wins'], -x['points_for']))

    for i, t in enumerate(standings_list):
        t['rank'] = i + 1

    return standings_list
from tables import COLORS, create_styled_table, format_dataframe_for_pdf, create_h2h_matrix_table


def clean(s):
    """Clean string for ASCII."""
    if s is None:
        return "Unknown"
    return str(s).encode('ascii', 'ignore').decode('ascii').strip() or 'Unknown'


def get_manager_name(full_name):
    """Extract manager name from 'Manager (Team)' format."""
    if '(' in str(full_name):
        return full_name.split('(')[0].strip()
    return full_name


class ReportGenerator:
    """Generate fantasy football reports."""

    def __init__(self, api: YahooFantasyAPI):
        self.api = api
        self.matchups_df = pd.DataFrame()
        self.standings_df = pd.DataFrame()
        self.trades_df = pd.DataFrame()
        self.adds_df = pd.DataFrame()
        self.seasons = []

    async def fetch_all_data(self, league_keys: List[Tuple[str, int]], job: Any):
        """Fetch all data for the given leagues."""
        all_matchups = []
        all_standings = []
        all_trades = []
        all_adds = []

        total_leagues = len(league_keys)

        for idx, (league_key, season) in enumerate(league_keys):
            progress = 20 + int((idx / total_leagues) * 60)
            job.progress = progress
            job.message = f"Fetching {season} data..."

            try:
                # Get teams
                teams = await self.api.get_league_teams(league_key)
                team_display = {}
                team_to_manager = {}

                for tk, tv in teams.items():
                    mgr = clean(tv.get("manager", "Unknown"))
                    name = clean(tv.get("name", "Unknown"))
                    team_display[tk] = f"{mgr} ({name})"
                    team_to_manager[tk] = mgr

                # Fetch matchups
                for week in range(1, 18):
                    matchups = await self.api.get_matchups(league_key, week)

                    if not matchups:
                        break

                    for m in matchups:
                        t1 = m["team1"]
                        t2 = m["team2"]

                        t1_key = t1.get("team_key", "")
                        t2_key = t2.get("team_key", "")

                        t1_name = team_display.get(t1_key, f"{clean(t1.get('manager'))} ({clean(t1.get('name'))})")
                        t2_name = team_display.get(t2_key, f"{clean(t2.get('manager'))} ({clean(t2.get('name'))})")

                        is_playoff = m.get("is_playoff", False)

                        all_matchups.append({
                            'season': season,
                            'week': week,
                            'team1_id': t1_key,
                            'team1_name': t1_name,
                            'team2_id': t2_key,
                            'team2_name': t2_name,
                            'score1': t1.get('points', 0),
                            'score2': t2.get('points', 0),
                            'is_playoff': is_playoff,
                            'is_championship': is_playoff and week >= 16,
                        })

                # Fetch standings
                standings = await self.api.get_league_standings(league_key)

                # Check if API returned valid standings data (any team has wins > 0)
                has_valid_standings = any(t.get('wins', 0) > 0 for t in standings)

                if not has_valid_standings and all_matchups:
                    # Calculate standings from matchup data as fallback
                    print(f"[STANDINGS] API didn't return wins data for {season}, calculating from matchups", flush=True)
                    standings = calculate_standings_from_matchups(all_matchups, teams, season)

                for i, t in enumerate(standings):
                    t_key = t.get("team_key", "")
                    t_name = team_display.get(t_key, f"{clean(t.get('manager'))} ({clean(t.get('name'))})")

                    all_standings.append({
                        'season': season,
                        'team_id': t_key,
                        'team_name': t_name,
                        'manager': clean(t.get('manager', 'Unknown')),
                        'rank': t.get('rank', i + 1),
                        'wins': t.get('wins', 0),
                        'losses': t.get('losses', 0),
                        'ties': t.get('ties', 0),
                        'points_for': t.get('points_for', 0),
                        'points_against': t.get('points_against', 0),
                        'made_playoffs': t.get('rank', i + 1) <= 6,
                        'won_championship': False,
                        'finals_appearance': False,
                    })

                # Fetch transactions
                try:
                    trade_txns = await self.api.get_transactions(league_key, "trade", 100)
                    add_txns = await self.api.get_transactions(league_key, "add", 200)

                    for txn in trade_txns:
                        ts = txn.get("timestamp")
                        txn_date = None
                        if ts:
                            try:
                                txn_date = datetime.fromtimestamp(int(ts))
                            except:
                                pass

                        trade_id = f"{season}_{ts}"
                        players = txn.get("players", {})

                        # Handle players being either a dict or a list
                        players_iter = []
                        if isinstance(players, dict):
                            players_iter = [(k, v) for k, v in players.items() if k != "count" and isinstance(v, dict)]
                        elif isinstance(players, list):
                            players_iter = [(str(i), p) for i, p in enumerate(players) if isinstance(p, dict)]

                        for key, val in players_iter:
                            player = val.get("player", [])
                            if not player:
                                continue

                            player_name = "Unknown"
                            pinfo = player[0] if isinstance(player[0], list) else []
                            for item in pinfo:
                                if isinstance(item, dict) and "name" in item:
                                    player_name = clean(item["name"].get("full", "Unknown"))

                            if len(player) > 1:
                                td = player[1].get("transaction_data", [{}])
                                if isinstance(td, list) and td:
                                    td = td[0]
                                dest = td.get("destination_team_key", "")
                                source = td.get("source_team_key", "")

                                all_trades.append({
                                    'season': season,
                                    'trade_id': trade_id,
                                    'date': txn_date,
                                    'player_name': player_name,
                                    'from_manager': team_to_manager.get(source, 'Unknown'),
                                    'to_manager': team_to_manager.get(dest, 'Unknown'),
                                })

                    for txn in add_txns:
                        ts = txn.get("timestamp")
                        txn_date = None
                        if ts:
                            try:
                                txn_date = datetime.fromtimestamp(int(ts))
                            except:
                                pass

                        players = txn.get("players", {})

                        # Handle players being either a dict or a list
                        players_iter = []
                        if isinstance(players, dict):
                            players_iter = [(k, v) for k, v in players.items() if k != "count" and isinstance(v, dict)]
                        elif isinstance(players, list):
                            players_iter = [(str(i), p) for i, p in enumerate(players) if isinstance(p, dict)]

                        for key, val in players_iter:
                            player = val.get("player", [])
                            if not player:
                                continue

                            player_name = "Unknown"
                            pinfo = player[0] if isinstance(player[0], list) else []
                            for item in pinfo:
                                if isinstance(item, dict) and "name" in item:
                                    player_name = clean(item["name"].get("full", "Unknown"))

                            if len(player) > 1:
                                td = player[1].get("transaction_data", {})
                                if isinstance(td, list) and td:
                                    td = td[0]

                                if td.get("type") in ("add", "claim"):
                                    dest = td.get("destination_team_key", "")
                                    source_type = td.get("source_type", "")

                                    all_adds.append({
                                        'season': season,
                                        'date': txn_date,
                                        'player_name': player_name,
                                        'manager': team_to_manager.get(dest, 'Unknown'),
                                        'source_type': source_type,
                                        'is_waiver': source_type == 'waivers',
                                    })
                except Exception as e:
                    print(f"Transaction error for {season}: {e}")

            except Exception as e:
                print(f"Error fetching {season}: {e}")

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        # Create DataFrames
        self.matchups_df = pd.DataFrame(all_matchups)
        self.standings_df = pd.DataFrame(all_standings)
        self.trades_df = pd.DataFrame(all_trades) if all_trades else pd.DataFrame()
        self.adds_df = pd.DataFrame(all_adds) if all_adds else pd.DataFrame()

        # Normalize names
        if not self.matchups_df.empty:
            self.matchups_df['team1_name'] = self.matchups_df['team1_name'].apply(get_manager_name)
            self.matchups_df['team2_name'] = self.matchups_df['team2_name'].apply(get_manager_name)
        if not self.standings_df.empty:
            self.standings_df['team_name'] = self.standings_df['team_name'].apply(get_manager_name)

        # Determine championships
        if not self.standings_df.empty and not self.matchups_df.empty:
            for season in self.standings_df['season'].unique():
                champ = self.matchups_df[
                    (self.matchups_df['season'] == season) &
                    (self.matchups_df['is_championship'])
                ]
                for _, m in champ.iterrows():
                    winner = m['team1_name'] if m['score1'] > m['score2'] else m['team2_name']
                    loser = m['team2_name'] if m['score1'] > m['score2'] else m['team1_name']
                    self.standings_df.loc[
                        (self.standings_df['season'] == season) &
                        (self.standings_df['team_name'] == winner),
                        'won_championship'
                    ] = True
                    self.standings_df.loc[
                        (self.standings_df['season'] == season) &
                        (self.standings_df['team_name'].isin([winner, loser])),
                        'finals_appearance'
                    ] = True

        self.seasons = sorted(self.matchups_df['season'].unique()) if not self.matchups_df.empty else []

    async def generate_pdf(self, league_name: str, output_path: Path):
        """Generate the comprehensive PDF report."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(letter),
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=36,
            spaceAfter=8,
            alignment=TA_CENTER,
            textColor=COLORS['primary'],
            fontName='Helvetica-Bold',
        )

        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=COLORS['accent'],
            fontName='Helvetica-Bold',
        )

        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceBefore=20,
            spaceAfter=8,
            textColor=COLORS['primary'],
            fontName='Helvetica-Bold',
        )

        subsection_style = ParagraphStyle(
            'SubsectionTitle',
            parent=styles['Heading3'],
            fontSize=11,
            spaceBefore=10,
            spaceAfter=6,
            textColor=COLORS['text_dark'],
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        )

        # Helper function to create tables
        def add_table_from_df(df, columns, column_names, number_format=None, max_rows=20, col_widths=None, title=None):
            if df.empty:
                return

            data = format_dataframe_for_pdf(df, columns, column_names, number_format, max_rows)
            table = create_styled_table(data, col_widths)

            if table:
                keep_elements = []
                if title:
                    keep_elements.append(Paragraph(title, subsection_style))
                keep_elements.append(table)
                keep_elements.append(Spacer(1, 0.15 * inch))
                elements.append(KeepTogether(keep_elements))

        def add_section(title):
            elements.append(Paragraph(title, section_style))
            elements.append(HRFlowable(width="100%", thickness=2, color=COLORS['accent']))

        def add_chart(chart_buffer, width=8.0, height=5.0, title=None):
            if chart_buffer is None:
                return
            chart_buffer.seek(0)
            img = Image(chart_buffer, width=width * inch, height=height * inch)
            keep_elements = []
            if title:
                keep_elements.append(Paragraph(title, subsection_style))
            keep_elements.append(img)
            keep_elements.append(Spacer(1, 0.15 * inch))
            elements.append(KeepTogether(keep_elements))

        # ===== Title Page =====
        elements.append(Spacer(1, 1 * inch))
        elements.append(Paragraph(league_name, title_style))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("HISTORICAL STATISTICS REPORT", subtitle_style))
        elements.append(Spacer(1, 0.3 * inch))

        if self.seasons:
            elements.append(Paragraph(
                f"Seasons: {min(self.seasons)} - {max(self.seasons)}",
                styles['Normal']
            ))

        team_count = len(self.matchups_df["team1_name"].unique()) if not self.matchups_df.empty else 0
        if team_count:
            elements.append(Paragraph(f"{team_count} Managers", styles['Normal']))

        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            styles['Normal']
        ))
        elements.append(PageBreak())

        # ===== Section 1: Head-to-Head Records =====
        add_section("1. Head-to-Head Records")

        h2h_matrix = head_to_head.build_h2h_matrix(self.matchups_df)
        h2h_numeric = head_to_head.get_h2h_numeric_matrix(self.matchups_df)

        if not h2h_numeric.empty:
            chart_buf = create_h2h_heatmap(h2h_numeric)
            add_chart(chart_buf, width=7.0, height=5.0, title="Win Percentage Heatmap")

        if not h2h_matrix.empty:
            table = create_h2h_matrix_table(h2h_matrix)
            if table:
                elements.append(Paragraph("Detailed Win-Loss Records", subsection_style))
                elements.append(table)
                elements.append(Spacer(1, 0.15 * inch))

        # ===== Section 2: Scoring Leaders =====
        add_section("2. Scoring Leaders")

        alltime_leaders = scoring.get_alltime_scoring_leaders(self.matchups_df)
        add_table_from_df(
            alltime_leaders,
            columns=["team_name", "total_points", "games", "ppg", "seasons"],
            column_names={"team_name": "Manager", "total_points": "Total Pts",
                          "games": "Games", "ppg": "PPG", "seasons": "Seasons"},
            number_format={"total_points": "{:.1f}", "ppg": "{:.2f}"},
            col_widths=[1.8*inch, 1.0*inch, 0.7*inch, 0.7*inch, 0.7*inch],
            title="All-Time Point Leaders",
        )

        weekly_highs = scoring.get_weekly_high_scores(self.matchups_df, top_n=15)
        add_table_from_df(
            weekly_highs,
            columns=["season", "week", "team_name", "points_for", "opponent_name"],
            column_names={"season": "Year", "week": "Wk", "team_name": "Manager",
                          "points_for": "Points", "opponent_name": "Opponent"},
            number_format={"points_for": "{:.2f}"},
            col_widths=[0.6*inch, 0.4*inch, 1.6*inch, 0.8*inch, 1.6*inch],
            title="Highest Single-Week Scores",
        )

        # ===== Section 3: Win/Loss Records =====
        add_section("3. Win/Loss Records")

        win_leaders = wins.get_alltime_win_leaders(self.matchups_df)
        add_table_from_df(
            win_leaders,
            columns=["team_name", "wins", "losses", "win_pct", "seasons"],
            column_names={"team_name": "Manager", "wins": "W", "losses": "L",
                          "win_pct": "Win %", "seasons": "Seasons"},
            number_format={"win_pct": "{:.1%}"},
            col_widths=[1.8*inch, 0.6*inch, 0.6*inch, 0.7*inch, 0.7*inch],
            title="All-Time Win Leaders",
        )

        best_teams = wins.get_best_teams_by_season(self.matchups_df)
        add_table_from_df(
            best_teams,
            columns=["season", "team_name", "wins", "losses", "win_pct"],
            column_names={"season": "Year", "team_name": "Manager", "wins": "W",
                          "losses": "L", "win_pct": "Win %"},
            number_format={"win_pct": "{:.1%}"},
            col_widths=[0.6*inch, 1.8*inch, 0.5*inch, 0.5*inch, 0.7*inch],
            title="Best Teams by Season",
        )

        worst_teams = wins.get_worst_teams_by_season(self.matchups_df)
        add_table_from_df(
            worst_teams,
            columns=["season", "team_name", "wins", "losses", "total_pts", "avg_ppg", "ppg_vs_median"],
            column_names={"season": "Year", "team_name": "Manager", "wins": "W",
                          "losses": "L", "total_pts": "Pts", "avg_ppg": "PPG", "ppg_vs_median": "vs Med"},
            number_format={"total_pts": "{:.0f}", "avg_ppg": "{:.1f}", "ppg_vs_median": "{:+.1f}"},
            col_widths=[0.5*inch, 1.4*inch, 0.4*inch, 0.4*inch, 0.6*inch, 0.55*inch, 0.55*inch],
            title="Worst Teams by Season",
        )

        # ===== Section 4: Streaks =====
        add_section("4. Win and Loss Streaks")

        win_streaks = wins.get_longest_win_streaks(self.matchups_df)
        add_table_from_df(
            win_streaks,
            columns=["team_name", "max_win_streak", "win_streak_end_season", "win_streak_end_week"],
            column_names={"team_name": "Manager", "max_win_streak": "Streak",
                          "win_streak_end_season": "End Year", "win_streak_end_week": "End Wk"},
            col_widths=[1.8*inch, 0.6*inch, 0.8*inch, 0.7*inch],
            title="Longest Win Streaks",
        )

        loss_streaks = wins.get_longest_loss_streaks(self.matchups_df)
        add_table_from_df(
            loss_streaks,
            columns=["team_name", "max_loss_streak", "loss_streak_end_season", "loss_streak_end_week"],
            column_names={"team_name": "Manager", "max_loss_streak": "Streak",
                          "loss_streak_end_season": "End Year", "loss_streak_end_week": "End Wk"},
            col_widths=[1.8*inch, 0.6*inch, 0.8*inch, 0.7*inch],
            title="Longest Losing Streaks",
        )

        # ===== Section 5: Championships & Playoffs =====
        add_section("5. Championships & Playoffs")

        if not self.standings_df.empty:
            podium_by_year = playoffs.get_podium_by_year(self.standings_df)
            add_table_from_df(
                podium_by_year,
                columns=["season", "1st", "2nd", "3rd"],
                column_names={"season": "Year", "1st": "1st Place", "2nd": "2nd Place", "3rd": "3rd Place"},
                col_widths=[0.6*inch, 1.6*inch, 1.6*inch, 1.6*inch],
                title="Playoff Podium by Year",
            )

            placement_counts = playoffs.get_placement_counts(self.standings_df)
            add_table_from_df(
                placement_counts,
                columns=["team_name", "1st", "2nd", "3rd", "total_podium", "seasons"],
                column_names={"team_name": "Manager", "1st": "1st", "2nd": "2nd",
                              "3rd": "3rd", "total_podium": "Total", "seasons": "Seasons"},
                col_widths=[1.8*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.6*inch, 0.7*inch],
                title="Total Podium Finishes by Manager",
            )

            playoff_apps = playoffs.get_playoff_appearances(self.standings_df)
            add_table_from_df(
                playoff_apps,
                columns=["team_name", "playoff_appearances", "seasons_played", "appearance_pct"],
                column_names={"team_name": "Manager", "playoff_appearances": "Apps",
                              "seasons_played": "Seasons", "appearance_pct": "Rate"},
                number_format={"appearance_pct": "{:.1%}"},
                col_widths=[1.8*inch, 0.7*inch, 0.7*inch, 0.7*inch],
                title="Playoff Appearances",
            )

        # ===== Section 6: Game Extremes =====
        add_section("6. Game Extremes")

        blowouts = games.get_biggest_blowouts(self.matchups_df, top_n=15)
        add_table_from_df(
            blowouts,
            columns=["season", "week", "winner", "loser", "winner_score", "loser_score", "margin"],
            column_names={"season": "Year", "week": "Wk", "winner": "Winner",
                          "loser": "Loser", "winner_score": "W Pts", "loser_score": "L Pts",
                          "margin": "Margin"},
            number_format={"winner_score": "{:.1f}", "loser_score": "{:.1f}", "margin": "{:.1f}"},
            col_widths=[0.5*inch, 0.4*inch, 1.5*inch, 1.5*inch, 0.6*inch, 0.6*inch, 0.6*inch],
            title="Biggest Blowouts",
        )

        closest = games.get_closest_games(self.matchups_df, top_n=15)
        add_table_from_df(
            closest,
            columns=["season", "week", "winner", "loser", "winner_score", "loser_score", "margin"],
            column_names={"season": "Year", "week": "Wk", "winner": "Winner",
                          "loser": "Loser", "winner_score": "W Pts", "loser_score": "L Pts",
                          "margin": "Margin"},
            number_format={"winner_score": "{:.1f}", "loser_score": "{:.1f}", "margin": "{:.2f}"},
            col_widths=[0.5*inch, 0.4*inch, 1.5*inch, 1.5*inch, 0.6*inch, 0.6*inch, 0.6*inch],
            title="Closest Games",
        )

        # ===== Section 7: Luck Analysis =====
        add_section("7. Luck Analysis")

        unlucky = luck.get_unlucky_losses(self.matchups_df, top_n=15)
        add_table_from_df(
            unlucky,
            columns=["season", "week", "team_name", "points_for", "opponent_name", "points_against"],
            column_names={"season": "Year", "week": "Wk", "team_name": "Manager",
                          "points_for": "Scored", "opponent_name": "Opponent", "points_against": "Opp"},
            number_format={"points_for": "{:.1f}", "points_against": "{:.1f}"},
            col_widths=[0.5*inch, 0.4*inch, 1.5*inch, 0.7*inch, 1.5*inch, 0.7*inch],
            title="Unluckiest Losses (High-Scoring Losses)",
        )

        lucky_wins = luck.get_lucky_wins(self.matchups_df, top_n=15)
        add_table_from_df(
            lucky_wins,
            columns=["season", "week", "team_name", "points_for", "opponent_name", "points_against"],
            column_names={"season": "Year", "week": "Wk", "team_name": "Manager",
                          "points_for": "Scored", "opponent_name": "Opponent", "points_against": "Opp"},
            number_format={"points_for": "{:.1f}", "points_against": "{:.1f}"},
            col_widths=[0.5*inch, 0.4*inch, 1.5*inch, 0.7*inch, 1.5*inch, 0.7*inch],
            title="Luckiest Wins (Low-Scoring Victories)",
        )

        all_play = luck.calculate_all_play_records(self.matchups_df)
        add_table_from_df(
            all_play,
            columns=["season", "team_name", "all_play_wins", "all_play_losses", "all_play_win_pct"],
            column_names={"season": "Year", "team_name": "Manager", "all_play_wins": "W",
                          "all_play_losses": "L", "all_play_win_pct": "Win %"},
            number_format={"all_play_win_pct": "{:.1%}"},
            col_widths=[0.6*inch, 1.8*inch, 0.5*inch, 0.5*inch, 0.7*inch],
            title="All-Play Records by Season",
        )

        alltime_all_play = luck.get_alltime_all_play_records(self.matchups_df)
        if not alltime_all_play.empty:
            alltime_all_play = alltime_all_play.copy()
            top_manager = alltime_all_play.iloc[0]["team_name"]
            alltime_all_play.loc[alltime_all_play["team_name"] == top_manager, "team_name"] = f"*** {top_manager} *** CHAMPION"

        add_table_from_df(
            alltime_all_play,
            columns=["team_name", "all_play_wins", "all_play_losses", "all_play_win_pct", "seasons"],
            column_names={"team_name": "Manager", "all_play_wins": "W",
                          "all_play_losses": "L", "all_play_win_pct": "Win %", "seasons": "Seasons"},
            number_format={"all_play_win_pct": "{:.1%}"},
            col_widths=[2.4*inch, 0.5*inch, 0.5*inch, 0.7*inch, 0.7*inch],
            title="All-Time All-Play Records (True Strength Champion)",
        )

        # ===== Section 8: Points Against =====
        add_section("8. Points Against (Schedule Luck)")

        pa_leaders = luck.get_points_against_leaders_by_year(self.matchups_df)
        add_table_from_df(
            pa_leaders,
            columns=["season", "team_name", "total_pa", "avg_pa", "wins", "pa_vs_avg"],
            column_names={"season": "Year", "team_name": "Manager", "total_pa": "Total PA",
                          "avg_pa": "Avg PA", "wins": "W", "pa_vs_avg": "vs Avg"},
            number_format={"total_pa": "{:.0f}", "avg_pa": "{:.1f}", "pa_vs_avg": "{:+.0f}"},
            col_widths=[0.5*inch, 1.4*inch, 0.7*inch, 0.6*inch, 0.4*inch, 0.6*inch],
            title="Most Points Against by Year (Unluckiest Schedule)",
        )

        # ===== Section 9: Transactions =====
        add_section("9. Transactions & Manager Activity")

        # Yearly scoring chart
        yearly_scoring = scoring.get_yearly_scoring_totals(self.matchups_df)
        if not yearly_scoring.empty:
            yearly_chart = create_yearly_scoring_chart(
                yearly_scoring,
                title="Total Points by Manager Over Time"
            )
            add_chart(yearly_chart, width=9.5, height=5.5, title="Yearly Scoring Totals")

        # Total moves by manager
        if not self.trades_df.empty or not self.adds_df.empty:
            total_moves = trades.get_total_moves_by_manager(self.trades_df, self.adds_df)
            if not total_moves.empty:
                add_table_from_df(
                    total_moves,
                    columns=["manager", "trades", "adds", "total_moves"],
                    column_names={"manager": "Manager", "trades": "Trades", "adds": "Adds", "total_moves": "Total Moves"},
                    col_widths=[1.8*inch, 0.7*inch, 0.7*inch, 0.9*inch],
                    title="Total Moves by Manager (Trades + Waiver Adds)",
                )

        # ===== Section 10: Scoring Consistency =====
        add_section("10. Scoring Consistency")

        consistent = consistency.get_most_consistent_teams(self.matchups_df, top_n=15)
        add_table_from_df(
            consistent,
            columns=["season", "team_name", "avg_score", "std_dev", "cv", "min_score", "max_score"],
            column_names={"season": "Year", "team_name": "Manager", "avg_score": "Avg",
                          "std_dev": "StdDev", "cv": "CV", "min_score": "Min", "max_score": "Max"},
            number_format={"avg_score": "{:.1f}", "std_dev": "{:.1f}", "cv": "{:.2f}",
                           "min_score": "{:.1f}", "max_score": "{:.1f}"},
            col_widths=[0.5*inch, 1.6*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.6*inch, 0.6*inch],
            title="Most Consistent Teams (Lowest Variance)",
        )

        volatile = consistency.get_most_volatile_teams(self.matchups_df, top_n=15)
        add_table_from_df(
            volatile,
            columns=["season", "team_name", "avg_score", "std_dev", "cv", "min_score", "max_score"],
            column_names={"season": "Year", "team_name": "Manager", "avg_score": "Avg",
                          "std_dev": "StdDev", "cv": "CV", "min_score": "Min", "max_score": "Max"},
            number_format={"avg_score": "{:.1f}", "std_dev": "{:.1f}", "cv": "{:.2f}",
                           "min_score": "{:.1f}", "max_score": "{:.1f}"},
            col_widths=[0.5*inch, 1.6*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.6*inch, 0.6*inch],
            title="Most Volatile Teams (Boom or Bust)",
        )

        # Build PDF
        doc.build(elements)
