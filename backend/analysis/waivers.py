"""Waiver wire analysis - evaluate pickup outcomes."""

import pandas as pd


def get_best_waiver_pickups(
    adds_df: pd.DataFrame,
    top_n: int = 50,
    waiver_only: bool = False,
) -> pd.DataFrame:
    """Get the best waiver wire/FA pickups by points after acquisition.

    Args:
        adds_df: DataFrame from fetch_all_transactions["adds"] with points_after column
        top_n: Number of pickups to return
        waiver_only: If True, only include waiver claims (not free agent pickups)

    Returns:
        DataFrame of best pickups sorted by points after acquisition
    """
    if adds_df.empty or "points_after" not in adds_df.columns:
        return pd.DataFrame()

    adds = adds_df.copy()

    if waiver_only:
        adds = adds[adds["is_waiver"] == True]

    # Filter out zero-point pickups
    adds = adds[adds["points_after"] > 0]

    best = adds.nlargest(top_n, "points_after")[
        ["season", "date", "team_id", "player_name", "position", "source_type", "points_after"]
    ]

    return best.reset_index(drop=True)


def get_waiver_pickup_summary(adds_df: pd.DataFrame) -> pd.DataFrame:
    """Get waiver wire activity summary by team.

    Args:
        adds_df: DataFrame from fetch_all_transactions["adds"] with points_after column

    Returns:
        DataFrame with pickup stats per team
    """
    if adds_df.empty:
        return pd.DataFrame()

    adds = adds_df.copy()

    # Basic counts
    summary = adds.groupby("team_id").agg({
        "player_id": "count",
        "is_waiver": "sum",
    }).reset_index()

    summary.columns = ["team_id", "total_adds", "waiver_claims"]
    summary["free_agent_adds"] = summary["total_adds"] - summary["waiver_claims"]

    # Add points if available
    if "points_after" in adds.columns:
        points = adds.groupby("team_id")["points_after"].sum().reset_index()
        points.columns = ["team_id", "total_points_from_adds"]
        summary = summary.merge(points, on="team_id")
        summary["avg_points_per_add"] = summary["total_points_from_adds"] / summary["total_adds"]

    return summary.sort_values("total_adds", ascending=False).reset_index(drop=True)


def get_waiver_activity_by_season(adds_df: pd.DataFrame) -> pd.DataFrame:
    """Get waiver wire activity breakdown by season.

    Args:
        adds_df: DataFrame from fetch_all_transactions["adds"]

    Returns:
        DataFrame with pickup counts per team per season
    """
    if adds_df.empty:
        return pd.DataFrame()

    adds = adds_df.copy()

    activity = adds.groupby(["season", "team_id"]).agg({
        "player_id": "count",
        "is_waiver": "sum",
    }).reset_index()

    activity.columns = ["season", "team_id", "total_adds", "waiver_claims"]

    if "points_after" in adds.columns:
        points = adds.groupby(["season", "team_id"])["points_after"].sum().reset_index()
        points.columns = ["season", "team_id", "points_from_adds"]
        activity = activity.merge(points, on=["season", "team_id"])

    return activity.sort_values(["season", "total_adds"], ascending=[False, False])


def get_position_pickup_success(adds_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze waiver pickup success by position.

    Args:
        adds_df: DataFrame from fetch_all_transactions["adds"] with points_after column

    Returns:
        DataFrame with pickup success by position
    """
    if adds_df.empty or "points_after" not in adds_df.columns:
        return pd.DataFrame()

    adds = adds_df.copy()

    position_stats = adds.groupby("position").agg({
        "player_id": "count",
        "points_after": ["sum", "mean", "max"],
    }).reset_index()

    position_stats.columns = [
        "position", "pickup_count", "total_points", "avg_points", "max_points"
    ]

    return position_stats.sort_values("total_points", ascending=False).reset_index(drop=True)


def get_waiver_mvps_by_season(adds_df: pd.DataFrame) -> pd.DataFrame:
    """Get the MVP waiver pickup for each season.

    Args:
        adds_df: DataFrame from fetch_all_transactions["adds"] with points_after column

    Returns:
        DataFrame with best pickup per season
    """
    if adds_df.empty or "points_after" not in adds_df.columns:
        return pd.DataFrame()

    adds = adds_df.copy()

    # Get the best pickup per season
    mvps = adds.loc[adds.groupby("season")["points_after"].idxmax()]

    return mvps[
        ["season", "team_id", "player_name", "position", "source_type", "points_after"]
    ].reset_index(drop=True)


def get_most_active_waiver_teams(adds_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get teams with the most waiver activity.

    Args:
        adds_df: DataFrame from fetch_all_transactions["adds"]
        top_n: Number of teams to return

    Returns:
        DataFrame of most active waiver wire teams
    """
    summary = get_waiver_pickup_summary(adds_df)

    if summary.empty:
        return pd.DataFrame()

    return summary.head(top_n)
