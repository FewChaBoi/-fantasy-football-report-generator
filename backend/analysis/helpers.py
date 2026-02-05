"""Helper functions for analysis modules."""

import pandas as pd


def get_team_scores_by_week(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Convert matchups to individual team scores per week.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with columns: season, week, team_id, team_name, points_for,
                                points_against, won, is_playoff
    """
    rows = []

    for _, m in matchups_df.iterrows():
        # Team 1's perspective
        rows.append({
            "season": m["season"],
            "week": m["week"],
            "team_id": m["team1_id"],
            "team_name": m["team1_name"],
            "opponent_id": m["team2_id"],
            "opponent_name": m["team2_name"],
            "points_for": m["score1"],
            "points_against": m["score2"],
            "won": m["score1"] > m["score2"],
            "is_playoff": m.get("is_playoff", False),
            "is_championship": m.get("is_championship", False),
        })

        # Team 2's perspective
        rows.append({
            "season": m["season"],
            "week": m["week"],
            "team_id": m["team2_id"],
            "team_name": m["team2_name"],
            "opponent_id": m["team1_id"],
            "opponent_name": m["team1_name"],
            "points_for": m["score2"],
            "points_against": m["score1"],
            "won": m["score2"] > m["score1"],
            "is_playoff": m.get("is_playoff", False),
            "is_championship": m.get("is_championship", False),
        })

    return pd.DataFrame(rows)
