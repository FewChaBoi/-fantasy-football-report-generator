"""Game analysis - blowouts and close games."""

import pandas as pd


def get_biggest_blowouts(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
    include_playoffs: bool = True,
) -> pd.DataFrame:
    """Get games with the largest margin of victory.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of games to return
        include_playoffs: Whether to include playoff games

    Returns:
        DataFrame with blowout game details
    """
    if matchups_df.empty:
        return pd.DataFrame()

    df = matchups_df.copy()
    if not include_playoffs:
        df = df[~df["is_playoff"]]

    # Calculate margin
    df["margin"] = abs(df["score1"] - df["score2"])

    # Determine winner and loser
    df["winner"] = df.apply(
        lambda x: x["team1_name"] if x["score1"] > x["score2"] else x["team2_name"],
        axis=1,
    )
    df["loser"] = df.apply(
        lambda x: x["team2_name"] if x["score1"] > x["score2"] else x["team1_name"],
        axis=1,
    )
    df["winner_score"] = df.apply(
        lambda x: x["score1"] if x["score1"] > x["score2"] else x["score2"],
        axis=1,
    )
    df["loser_score"] = df.apply(
        lambda x: x["score2"] if x["score1"] > x["score2"] else x["score1"],
        axis=1,
    )

    blowouts = df.nlargest(top_n, "margin")[
        ["season", "week", "winner", "loser", "winner_score", "loser_score", "margin", "is_playoff"]
    ]

    return blowouts.reset_index(drop=True)


def get_closest_games(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
    include_playoffs: bool = True,
) -> pd.DataFrame:
    """Get games with the smallest margin of victory.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of games to return
        include_playoffs: Whether to include playoff games

    Returns:
        DataFrame with close game details
    """
    if matchups_df.empty:
        return pd.DataFrame()

    df = matchups_df.copy()
    if not include_playoffs:
        df = df[~df["is_playoff"]]

    # Filter out ties (margin = 0) unless they're actual games
    df["margin"] = abs(df["score1"] - df["score2"])

    # Filter out incomplete games (both scores 0)
    df = df[(df["score1"] > 0) | (df["score2"] > 0)]

    # Determine winner and loser
    df["winner"] = df.apply(
        lambda x: x["team1_name"] if x["score1"] > x["score2"] else x["team2_name"],
        axis=1,
    )
    df["loser"] = df.apply(
        lambda x: x["team2_name"] if x["score1"] > x["score2"] else x["team1_name"],
        axis=1,
    )
    df["winner_score"] = df.apply(
        lambda x: x["score1"] if x["score1"] > x["score2"] else x["score2"],
        axis=1,
    )
    df["loser_score"] = df.apply(
        lambda x: x["score2"] if x["score1"] > x["score2"] else x["score1"],
        axis=1,
    )

    closest = df.nsmallest(top_n, "margin")[
        ["season", "week", "winner", "loser", "winner_score", "loser_score", "margin", "is_playoff"]
    ]

    return closest.reset_index(drop=True)


def get_highest_combined_scores(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
) -> pd.DataFrame:
    """Get games with the highest combined scores.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of games to return

    Returns:
        DataFrame with high-scoring game details
    """
    if matchups_df.empty:
        return pd.DataFrame()

    df = matchups_df.copy()
    df["combined_score"] = df["score1"] + df["score2"]

    highest = df.nlargest(top_n, "combined_score")[
        ["season", "week", "team1_name", "team2_name", "score1", "score2", "combined_score", "is_playoff"]
    ]

    return highest.reset_index(drop=True)


def get_lowest_combined_scores(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
) -> pd.DataFrame:
    """Get games with the lowest combined scores.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of games to return

    Returns:
        DataFrame with low-scoring game details
    """
    if matchups_df.empty:
        return pd.DataFrame()

    df = matchups_df.copy()

    # Filter out incomplete games
    df = df[(df["score1"] > 0) & (df["score2"] > 0)]
    df["combined_score"] = df["score1"] + df["score2"]

    lowest = df.nsmallest(top_n, "combined_score")[
        ["season", "week", "team1_name", "team2_name", "score1", "score2", "combined_score", "is_playoff"]
    ]

    return lowest.reset_index(drop=True)


def get_game_margin_distribution(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get distribution of game margins.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with margin ranges and counts
    """
    if matchups_df.empty:
        return pd.DataFrame()

    df = matchups_df.copy()
    df["margin"] = abs(df["score1"] - df["score2"])

    # Define margin buckets
    bins = [0, 5, 10, 20, 30, 50, 100, float("inf")]
    labels = ["0-5", "5-10", "10-20", "20-30", "30-50", "50-100", "100+"]

    df["margin_range"] = pd.cut(df["margin"], bins=bins, labels=labels, right=False)

    distribution = df.groupby("margin_range", observed=True).size().reset_index(name="count")
    distribution["percentage"] = distribution["count"] / distribution["count"].sum() * 100

    return distribution
