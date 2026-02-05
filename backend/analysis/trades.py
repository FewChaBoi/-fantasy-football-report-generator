"""Trade analysis - evaluate trade outcomes."""

import pandas as pd
from collections import defaultdict


def analyze_trades(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze trade outcomes based on post-trade player points.

    Args:
        trades_df: DataFrame from fetch_all_transactions["trades"] with points_after column

    Returns:
        DataFrame with trade outcomes aggregated by trade event
    """
    if trades_df.empty or "points_after" not in trades_df.columns:
        return pd.DataFrame()

    # Group trades by date and teams involved to identify trade events
    trades = trades_df.copy()

    # Create a trade event identifier
    trades["trade_event"] = (
        trades["season"].astype(str) + "_" +
        trades["date"].astype(str) + "_" +
        trades[["from_team_id", "to_team_id"]].apply(
            lambda x: "_".join(sorted([str(x[0]), str(x[1])])), axis=1
        )
    )

    # Aggregate by trade event
    trade_results = []

    for event_id, event_trades in trades.groupby("trade_event"):
        # Get unique teams in this trade
        teams = set(event_trades["from_team_id"].unique()) | set(event_trades["to_team_id"].unique())

        if len(teams) != 2:
            continue

        team_a, team_b = sorted(list(teams))

        # Points team A acquired (players moving TO team A)
        team_a_acquired = event_trades[event_trades["to_team_id"] == team_a]["points_after"].sum()
        # Points team B acquired (players moving TO team B)
        team_b_acquired = event_trades[event_trades["to_team_id"] == team_b]["points_after"].sum()

        # Determine winner
        diff = team_a_acquired - team_b_acquired
        if diff > 0:
            winner = team_a
            loser = team_b
            winner_points = team_a_acquired
            loser_points = team_b_acquired
        else:
            winner = team_b
            loser = team_a
            winner_points = team_b_acquired
            loser_points = team_a_acquired
            diff = -diff

        # Get player names for each side
        players_to_a = event_trades[event_trades["to_team_id"] == team_a]["player_name"].tolist()
        players_to_b = event_trades[event_trades["to_team_id"] == team_b]["player_name"].tolist()

        trade_results.append({
            "season": event_trades["season"].iloc[0],
            "date": event_trades["date"].iloc[0],
            "winner_team_id": winner,
            "loser_team_id": loser,
            "winner_points": winner_points,
            "loser_points": loser_points,
            "point_differential": diff,
            "winner_acquired": ", ".join(players_to_a if winner == team_a else players_to_b),
            "loser_acquired": ", ".join(players_to_b if winner == team_a else players_to_a),
        })

    return pd.DataFrame(trade_results)


def get_worst_trades(trades_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Get the worst trades by point differential.

    Args:
        trades_df: DataFrame from fetch_all_transactions["trades"] with points_after
        top_n: Number of trades to return

    Returns:
        DataFrame of worst trades (from losing team's perspective)
    """
    analyzed = analyze_trades(trades_df)

    if analyzed.empty:
        return pd.DataFrame()

    # Sort by point differential (biggest losses)
    worst = analyzed.nlargest(top_n, "point_differential")

    return worst[
        ["season", "date", "loser_team_id", "winner_team_id",
         "loser_acquired", "winner_acquired", "loser_points", "winner_points", "point_differential"]
    ].reset_index(drop=True)


def get_best_trades(trades_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Get the best trades by point differential.

    Args:
        trades_df: DataFrame from fetch_all_transactions["trades"] with points_after
        top_n: Number of trades to return

    Returns:
        DataFrame of best trades (from winning team's perspective)
    """
    analyzed = analyze_trades(trades_df)

    if analyzed.empty:
        return pd.DataFrame()

    # Sort by point differential (biggest wins)
    best = analyzed.nlargest(top_n, "point_differential")

    return best[
        ["season", "date", "winner_team_id", "loser_team_id",
         "winner_acquired", "loser_acquired", "winner_points", "loser_points", "point_differential"]
    ].reset_index(drop=True)


def get_trade_frequency(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Get trade frequency by team.

    Args:
        trades_df: DataFrame from fetch_all_transactions["trades"]

    Returns:
        DataFrame with trade counts per team
    """
    if trades_df.empty:
        return pd.DataFrame()

    trades = trades_df.copy()

    # Count trades as sender
    sent = trades.groupby("from_team_id").size().reset_index(name="players_sent")
    sent.columns = ["team_id", "players_sent"]

    # Count trades as receiver
    received = trades.groupby("to_team_id").size().reset_index(name="players_received")
    received.columns = ["team_id", "players_received"]

    # Merge
    freq = sent.merge(received, on="team_id", how="outer").fillna(0)
    freq["total_players_traded"] = freq["players_sent"] + freq["players_received"]

    return freq.sort_values("total_players_traded", ascending=False).reset_index(drop=True)


def get_trade_win_rate(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Get trade win rate by team.

    Args:
        trades_df: DataFrame from fetch_all_transactions["trades"] with points_after

    Returns:
        DataFrame with trade win rate per team
    """
    analyzed = analyze_trades(trades_df)

    if analyzed.empty:
        return pd.DataFrame()

    # Count wins and losses for each team
    wins = analyzed.groupby("winner_team_id").size().reset_index(name="trade_wins")
    losses = analyzed.groupby("loser_team_id").size().reset_index(name="trade_losses")

    wins.columns = ["team_id", "trade_wins"]
    losses.columns = ["team_id", "trade_losses"]

    # Merge
    rates = wins.merge(losses, on="team_id", how="outer").fillna(0)
    rates["total_trades"] = rates["trade_wins"] + rates["trade_losses"]
    rates["trade_win_rate"] = rates["trade_wins"] / rates["total_trades"]

    return rates.sort_values("trade_win_rate", ascending=False).reset_index(drop=True)


def get_trade_counts_by_manager(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Get total trade count per manager across all seasons.

    Args:
        trades_df: DataFrame with trade data including 'from_manager' and 'to_manager'

    Returns:
        DataFrame with manager, trades, seasons involved
    """
    if trades_df.empty:
        return pd.DataFrame()

    # Count unique trades per manager (as either sender or receiver)
    # Group by trade_id to count unique trades, not player moves
    if 'trade_id' not in trades_df.columns:
        return pd.DataFrame()

    trades = trades_df.copy()

    # Get unique trades per manager
    from_trades = trades.groupby('from_manager').agg({
        'trade_id': 'nunique',
        'season': 'nunique'
    }).reset_index()
    from_trades.columns = ['manager', 'trades_as_sender', 'seasons']

    to_trades = trades.groupby('to_manager').agg({
        'trade_id': 'nunique',
    }).reset_index()
    to_trades.columns = ['manager', 'trades_as_receiver']

    # Merge - a trade is counted once per manager involved
    result = from_trades.merge(to_trades, on='manager', how='outer').fillna(0)

    # Total unique trades (max of sender/receiver since same trade counted both ways)
    result['total_trades'] = result[['trades_as_sender', 'trades_as_receiver']].max(axis=1).astype(int)
    result['seasons'] = result['seasons'].astype(int)

    return result[['manager', 'total_trades', 'seasons']].sort_values(
        'total_trades', ascending=False
    ).reset_index(drop=True)


def get_total_moves_by_manager(trades_df: pd.DataFrame, adds_df: pd.DataFrame) -> pd.DataFrame:
    """Get total moves (trades + waiver/FA adds) per manager.

    Args:
        trades_df: DataFrame with trade data
        adds_df: DataFrame with add data

    Returns:
        DataFrame with manager, trades, adds, total moves
    """
    # Count trades
    trade_counts = pd.DataFrame()
    if not trades_df.empty and 'from_manager' in trades_df.columns:
        # Count unique trades per manager
        from_trades = trades_df.groupby('from_manager')['trade_id'].nunique().reset_index()
        from_trades.columns = ['manager', 'trades']
        trade_counts = from_trades

    # Count adds
    add_counts = pd.DataFrame()
    if not adds_df.empty and 'manager' in adds_df.columns:
        add_counts = adds_df.groupby('manager').size().reset_index(name='adds')

    # Merge
    if trade_counts.empty and add_counts.empty:
        return pd.DataFrame()

    if trade_counts.empty:
        result = add_counts.copy()
        result['trades'] = 0
    elif add_counts.empty:
        result = trade_counts.copy()
        result['adds'] = 0
    else:
        result = trade_counts.merge(add_counts, on='manager', how='outer').fillna(0)

    result['trades'] = result['trades'].astype(int)
    result['adds'] = result['adds'].astype(int)
    result['total_moves'] = result['trades'] + result['adds']

    return result[['manager', 'trades', 'adds', 'total_moves']].sort_values(
        'total_moves', ascending=False
    ).reset_index(drop=True)
