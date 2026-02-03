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
from matplotlib.backends.backend_agg import FigureCanvasAgg

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


# Color scheme
COLORS = {
    'primary': colors.Color(0.1, 0.1, 0.15),
    'accent': colors.Color(1.0, 0.5, 0.0),
    'accent_gold': colors.Color(1.0, 0.84, 0.0),
    'white': colors.white,
    'light_gray': colors.Color(0.95, 0.95, 0.95),
    'text_dark': colors.Color(0.2, 0.2, 0.2),
}


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
                    trades = await self.api.get_transactions(league_key, "trade", 100)
                    adds = await self.api.get_transactions(league_key, "add", 200)

                    for txn in trades:
                        ts = txn.get("timestamp")
                        txn_date = None
                        if ts:
                            try:
                                txn_date = datetime.fromtimestamp(int(ts))
                            except:
                                pass

                        trade_id = f"{season}_{ts}"
                        players = txn.get("players", {})

                        for key, val in players.items():
                            if key == "count" or not isinstance(val, dict):
                                continue

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

                    for txn in adds:
                        ts = txn.get("timestamp")
                        txn_date = None
                        if ts:
                            try:
                                txn_date = datetime.fromtimestamp(int(ts))
                            except:
                                pass

                        players = txn.get("players", {})

                        for key, val in players.items():
                            if key == "count" or not isinstance(val, dict):
                                continue

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
        """Generate the PDF report."""
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

        # Title Page
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

        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            styles['Normal']
        ))
        elements.append(PageBreak())

        # Helper function to create tables
        def create_table(data, col_widths=None):
            if not data:
                return None

            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLORS['white']),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLORS['white'], COLORS['light_gray']]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            return table

        # Section 1: Scoring Leaders
        elements.append(Paragraph("1. Scoring Leaders", section_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=COLORS['accent']))

        if not self.matchups_df.empty:
            # All-time scoring leaders
            team_scores = self._get_team_scores()
            team_scores = team_scores[~team_scores['is_playoff']]

            alltime = team_scores.groupby('team_name').agg({
                'points_for': 'sum',
                'week': 'count',
                'season': 'nunique',
            }).reset_index()
            alltime.columns = ['Manager', 'Total Points', 'Games', 'Seasons']
            alltime['PPG'] = alltime['Total Points'] / alltime['Games']
            alltime = alltime.sort_values('Total Points', ascending=False).head(15)

            data = [['Manager', 'Total Pts', 'Games', 'PPG', 'Seasons']]
            for _, row in alltime.iterrows():
                data.append([
                    row['Manager'],
                    f"{row['Total Points']:.1f}",
                    str(row['Games']),
                    f"{row['PPG']:.2f}",
                    str(row['Seasons']),
                ])

            elements.append(Paragraph("All-Time Scoring Leaders", subsection_style))
            table = create_table(data, [1.8*inch, 0.9*inch, 0.7*inch, 0.7*inch, 0.7*inch])
            if table:
                elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Section 2: Win/Loss Records
        elements.append(Paragraph("2. Win/Loss Records", section_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=COLORS['accent']))

        if not self.matchups_df.empty:
            team_scores = self._get_team_scores()
            team_scores = team_scores[~team_scores['is_playoff']]

            win_records = team_scores.groupby('team_name').agg({
                'won': 'sum',
                'week': 'count',
                'season': 'nunique',
            }).reset_index()
            win_records.columns = ['Manager', 'Wins', 'Games', 'Seasons']
            win_records['Losses'] = win_records['Games'] - win_records['Wins']
            win_records['Win %'] = win_records['Wins'] / win_records['Games']
            win_records = win_records.sort_values('Wins', ascending=False).head(15)

            data = [['Manager', 'W', 'L', 'Win %', 'Seasons']]
            for _, row in win_records.iterrows():
                data.append([
                    row['Manager'],
                    str(int(row['Wins'])),
                    str(int(row['Losses'])),
                    f"{row['Win %']:.1%}",
                    str(row['Seasons']),
                ])

            elements.append(Paragraph("All-Time Win Leaders", subsection_style))
            table = create_table(data, [1.8*inch, 0.6*inch, 0.6*inch, 0.7*inch, 0.7*inch])
            if table:
                elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Section 3: Championships
        elements.append(Paragraph("3. Championships & Playoffs", section_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=COLORS['accent']))

        if not self.standings_df.empty:
            # Podium by year
            podium_data = [['Season', '1st Place', '2nd Place', '3rd Place']]
            for season in sorted(self.standings_df['season'].unique(), reverse=True):
                season_df = self.standings_df[self.standings_df['season'] == season]
                first = season_df[season_df['rank'] == 1]['team_name'].values
                second = season_df[season_df['rank'] == 2]['team_name'].values
                third = season_df[season_df['rank'] == 3]['team_name'].values

                podium_data.append([
                    str(season),
                    first[0] if len(first) > 0 else "",
                    second[0] if len(second) > 0 else "",
                    third[0] if len(third) > 0 else "",
                ])

            elements.append(Paragraph("Playoff Podium by Year", subsection_style))
            table = create_table(podium_data, [0.6*inch, 1.6*inch, 1.6*inch, 1.6*inch])
            if table:
                elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

            # Championship counts
            champs = self.standings_df.copy()
            champs['first'] = (champs['rank'] == 1).astype(int)
            champs['second'] = (champs['rank'] == 2).astype(int)
            champs['third'] = (champs['rank'] == 3).astype(int)

            placements = champs.groupby('team_name').agg({
                'first': 'sum',
                'second': 'sum',
                'third': 'sum',
                'season': 'count',
            }).reset_index()
            placements.columns = ['Manager', '1st', '2nd', '3rd', 'Seasons']
            placements['Total'] = placements['1st'] + placements['2nd'] + placements['3rd']
            placements = placements.sort_values(['1st', '2nd', '3rd'], ascending=False).head(15)

            data = [['Manager', '1st', '2nd', '3rd', 'Total', 'Seasons']]
            for _, row in placements.iterrows():
                data.append([
                    row['Manager'],
                    str(int(row['1st'])),
                    str(int(row['2nd'])),
                    str(int(row['3rd'])),
                    str(int(row['Total'])),
                    str(row['Seasons']),
                ])

            elements.append(Paragraph("Podium Finishes by Manager", subsection_style))
            table = create_table(data, [1.8*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.6*inch, 0.7*inch])
            if table:
                elements.append(table)

        # Section 4: Transactions
        if not self.trades_df.empty or not self.adds_df.empty:
            elements.append(PageBreak())
            elements.append(Paragraph("4. Transactions & Activity", section_style))
            elements.append(HRFlowable(width="100%", thickness=2, color=COLORS['accent']))

            # Total moves by manager
            trade_counts = pd.DataFrame()
            add_counts = pd.DataFrame()

            if not self.trades_df.empty and 'from_manager' in self.trades_df.columns:
                trade_counts = self.trades_df.groupby('from_manager')['trade_id'].nunique().reset_index()
                trade_counts.columns = ['Manager', 'Trades']

            if not self.adds_df.empty and 'manager' in self.adds_df.columns:
                add_counts = self.adds_df.groupby('manager').size().reset_index(name='Adds')
                add_counts.columns = ['Manager', 'Adds']

            if not trade_counts.empty or not add_counts.empty:
                if trade_counts.empty:
                    moves = add_counts.copy()
                    moves['Trades'] = 0
                elif add_counts.empty:
                    moves = trade_counts.copy()
                    moves['Adds'] = 0
                else:
                    moves = trade_counts.merge(add_counts, on='Manager', how='outer').fillna(0)

                moves['Trades'] = moves['Trades'].astype(int)
                moves['Adds'] = moves['Adds'].astype(int)
                moves['Total'] = moves['Trades'] + moves['Adds']
                moves = moves.sort_values('Total', ascending=False).head(15)

                data = [['Manager', 'Trades', 'Adds', 'Total Moves']]
                for _, row in moves.iterrows():
                    data.append([
                        row['Manager'],
                        str(row['Trades']),
                        str(row['Adds']),
                        str(row['Total']),
                    ])

                elements.append(Paragraph("Total Moves by Manager", subsection_style))
                table = create_table(data, [1.8*inch, 0.7*inch, 0.7*inch, 0.9*inch])
                if table:
                    elements.append(table)

        # Build PDF
        doc.build(elements)

    def _get_team_scores(self) -> pd.DataFrame:
        """Get team scores by week from matchups."""
        if self.matchups_df.empty:
            return pd.DataFrame()

        team1 = self.matchups_df[['season', 'week', 'team1_name', 'score1', 'score2', 'is_playoff']].copy()
        team1.columns = ['season', 'week', 'team_name', 'points_for', 'points_against', 'is_playoff']
        team1['won'] = team1['points_for'] > team1['points_against']

        team2 = self.matchups_df[['season', 'week', 'team2_name', 'score2', 'score1', 'is_playoff']].copy()
        team2.columns = ['season', 'week', 'team_name', 'points_for', 'points_against', 'is_playoff']
        team2['won'] = team2['points_for'] > team2['points_against']

        return pd.concat([team1, team2], ignore_index=True)
