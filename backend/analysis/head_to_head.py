"""Head-to-head record analysis."""

import pandas as pd
import numpy as np


def build_h2h_matrix(matchups_df: pd.DataFrame, include_playoffs: bool = True) -> pd.DataFrame:
    """Build head-to-head record matrix between all teams.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        include_playoffs: Whether to include playoff games

    Returns:
        DataFrame matrix with team names as index and columns,
        values are "W-L" strings
    """
    if matchups_df.empty:
        return pd.DataFrame()

    df = matchups_df.copy()
    if not include_playoffs:
        df = df[~df["is_playoff"]]

    # Get all unique team names
    all_teams = sorted(set(df["team1_name"].unique()) | set(df["team2_name"].unique()))

    # Initialize records dictionary
    records = {team: {other: {"wins": 0, "losses": 0} for other in all_teams} for team in all_teams}

    # Process each matchup
    for _, m in df.iterrows():
        t1, t2 = m["team1_name"], m["team2_name"]
        s1, s2 = m["score1"], m["score2"]

        if s1 > s2:
            records[t1][t2]["wins"] += 1
            records[t2][t1]["losses"] += 1
        elif s2 > s1:
            records[t2][t1]["wins"] += 1
            records[t1][t2]["losses"] += 1
        # Ties are not counted

    # Build matrix
    matrix_data = []
    for team in all_teams:
        row = {}
        for other in all_teams:
            if team == other:
                row[other] = "-"
            else:
                w = records[team][other]["wins"]
                l = records[team][other]["losses"]
                row[other] = f"{w}-{l}"
        matrix_data.append(row)

    matrix = pd.DataFrame(matrix_data, index=all_teams)
    matrix.columns = all_teams

    return matrix


def get_h2h_numeric_matrix(matchups_df: pd.DataFrame, include_playoffs: bool = True) -> pd.DataFrame:
    """Build numeric head-to-head win percentage matrix for heatmap visualization.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        include_playoffs: Whether to include playoff games

    Returns:
        DataFrame matrix with win percentages (0.0 to 1.0)
    """
    if matchups_df.empty:
        return pd.DataFrame()

    df = matchups_df.copy()
    if not include_playoffs:
        df = df[~df["is_playoff"]]

    all_teams = sorted(set(df["team1_name"].unique()) | set(df["team2_name"].unique()))
    records = {team: {other: {"wins": 0, "total": 0} for other in all_teams} for team in all_teams}

    for _, m in df.iterrows():
        t1, t2 = m["team1_name"], m["team2_name"]
        s1, s2 = m["score1"], m["score2"]

        records[t1][t2]["total"] += 1
        records[t2][t1]["total"] += 1

        if s1 > s2:
            records[t1][t2]["wins"] += 1
        elif s2 > s1:
            records[t2][t1]["wins"] += 1
        else:
            # Tie counts as 0.5 win for each
            records[t1][t2]["wins"] += 0.5
            records[t2][t1]["wins"] += 0.5

    matrix_data = []
    for team in all_teams:
        row = {}
        for other in all_teams:
            if team == other:
                row[other] = np.nan
            elif records[team][other]["total"] == 0:
                row[other] = np.nan
            else:
                row[other] = records[team][other]["wins"] / records[team][other]["total"]
        matrix_data.append(row)

    matrix = pd.DataFrame(matrix_data, index=all_teams)
    matrix.columns = all_teams

    return matrix


def get_h2h_detailed(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get detailed head-to-head records for all team pairs.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with team1, team2, wins, losses, ties, win_pct, total_games
    """
    if matchups_df.empty:
        return pd.DataFrame()

    records = {}

    for _, m in matchups_df.iterrows():
        t1, t2 = m["team1_name"], m["team2_name"]
        s1, s2 = m["score1"], m["score2"]

        # Use sorted tuple as key to avoid duplicates
        key = tuple(sorted([t1, t2]))

        if key not in records:
            records[key] = {"team1": key[0], "team2": key[1], "wins1": 0, "wins2": 0, "ties": 0}

        # Determine which team is team1 in our record
        if t1 == key[0]:
            if s1 > s2:
                records[key]["wins1"] += 1
            elif s2 > s1:
                records[key]["wins2"] += 1
            else:
                records[key]["ties"] += 1
        else:
            if s2 > s1:
                records[key]["wins1"] += 1
            elif s1 > s2:
                records[key]["wins2"] += 1
            else:
                records[key]["ties"] += 1

    # Convert to DataFrame
    rows = []
    for rec in records.values():
        total = rec["wins1"] + rec["wins2"] + rec["ties"]
        rows.append({
            "team1": rec["team1"],
            "team2": rec["team2"],
            "team1_wins": rec["wins1"],
            "team2_wins": rec["wins2"],
            "ties": rec["ties"],
            "total_games": total,
            "team1_win_pct": rec["wins1"] / total if total > 0 else 0,
        })

    return pd.DataFrame(rows).sort_values("total_games", ascending=False)


def get_most_played_rivalries(matchups_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get the most-played matchups (rivalries).

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of rivalries to return

    Returns:
        DataFrame of top rivalries sorted by games played
    """
    detailed = get_h2h_detailed(matchups_df)
    if detailed.empty:
        return detailed

    return detailed.head(top_n)
