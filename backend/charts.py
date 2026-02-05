"""Chart generation for PDF reports using matplotlib."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from io import BytesIO
from pathlib import Path


def create_h2h_heatmap(h2h_matrix: pd.DataFrame, output_path: str = None) -> BytesIO:
    """Create a head-to-head heatmap.

    Args:
        h2h_matrix: Numeric H2H matrix from get_h2h_numeric_matrix
        output_path: Optional path to save the image

    Returns:
        BytesIO buffer containing the image
    """
    if h2h_matrix.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 10))

    # Create heatmap
    im = ax.imshow(h2h_matrix.values, cmap="RdYlGn", vmin=0, vmax=1)

    # Set ticks
    ax.set_xticks(np.arange(len(h2h_matrix.columns)))
    ax.set_yticks(np.arange(len(h2h_matrix.index)))
    ax.set_xticklabels(h2h_matrix.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(h2h_matrix.index, fontsize=8)

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Win Percentage", rotation=-90, va="bottom")

    # Add title
    ax.set_title("Head-to-Head Win Percentage", fontsize=14, fontweight="bold")

    plt.tight_layout()

    # Save to buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        buf.seek(0)

    return buf


def create_bar_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str = None,
    ylabel: str = None,
    color: str = "#1f77b4",
    horizontal: bool = False,
    output_path: str = None,
) -> BytesIO:
    """Create a bar chart.

    Args:
        data: DataFrame with data to plot
        x_col: Column name for x-axis (categories)
        y_col: Column name for y-axis (values)
        title: Chart title
        xlabel: X-axis label
        ylabel: Y-axis label
        color: Bar color
        horizontal: If True, create horizontal bar chart
        output_path: Optional path to save the image

    Returns:
        BytesIO buffer containing the image
    """
    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    if horizontal:
        ax.barh(data[x_col], data[y_col], color=color)
        ax.set_xlabel(ylabel or y_col)
        ax.set_ylabel(xlabel or x_col)
        ax.invert_yaxis()
    else:
        ax.bar(data[x_col], data[y_col], color=color)
        ax.set_xlabel(xlabel or x_col)
        ax.set_ylabel(ylabel or y_col)
        plt.xticks(rotation=45, ha="right")

    ax.set_title(title, fontsize=14, fontweight="bold")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        buf.seek(0)

    return buf


def create_line_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    group_col: str = None,
    xlabel: str = None,
    ylabel: str = None,
    output_path: str = None,
) -> BytesIO:
    """Create a line chart.

    Args:
        data: DataFrame with data to plot
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        group_col: Optional column to group lines by
        xlabel: X-axis label
        ylabel: Y-axis label
        output_path: Optional path to save the image

    Returns:
        BytesIO buffer containing the image
    """
    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))

    if group_col:
        for name, group in data.groupby(group_col):
            ax.plot(group[x_col], group[y_col], label=name, marker="o")
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
    else:
        ax.plot(data[x_col], data[y_col], marker="o", color="#1f77b4")

    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or y_col)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        buf.seek(0)

    return buf


def create_stacked_bar_chart(
    data: pd.DataFrame,
    x_col: str,
    y_cols: list,
    title: str,
    xlabel: str = None,
    ylabel: str = None,
    colors: list = None,
    output_path: str = None,
) -> BytesIO:
    """Create a stacked bar chart.

    Args:
        data: DataFrame with data to plot
        x_col: Column name for x-axis (categories)
        y_cols: List of column names to stack
        title: Chart title
        xlabel: X-axis label
        ylabel: Y-axis label
        colors: List of colors for each stack
        output_path: Optional path to save the image

    Returns:
        BytesIO buffer containing the image
    """
    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))

    if colors is None:
        colors = plt.cm.tab10.colors[:len(y_cols)]

    bottom = np.zeros(len(data))
    for i, col in enumerate(y_cols):
        ax.bar(data[x_col], data[col], bottom=bottom, label=col, color=colors[i])
        bottom += data[col].values

    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or "Value")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend()
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        buf.seek(0)

    return buf


def create_pie_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    output_path: str = None,
) -> BytesIO:
    """Create a pie chart.

    Args:
        data: DataFrame with data to plot
        label_col: Column name for labels
        value_col: Column name for values
        title: Chart title
        output_path: Optional path to save the image

    Returns:
        BytesIO buffer containing the image
    """
    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 8))

    ax.pie(
        data[value_col],
        labels=data[label_col],
        autopct="%1.1f%%",
        startangle=90,
    )
    ax.set_title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        buf.seek(0)

    return buf


def create_scatter_plot(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    label_col: str = None,
    xlabel: str = None,
    ylabel: str = None,
    color_col: str = None,
    output_path: str = None,
) -> BytesIO:
    """Create a scatter plot.

    Args:
        data: DataFrame with data to plot
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        label_col: Optional column for point labels
        xlabel: X-axis label
        ylabel: Y-axis label
        color_col: Optional column for point colors
        output_path: Optional path to save the image

    Returns:
        BytesIO buffer containing the image
    """
    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 8))

    if color_col:
        scatter = ax.scatter(data[x_col], data[y_col], c=data[color_col], cmap="viridis", alpha=0.7)
        plt.colorbar(scatter, label=color_col)
    else:
        ax.scatter(data[x_col], data[y_col], alpha=0.7)

    if label_col:
        for _, row in data.iterrows():
            ax.annotate(
                row[label_col],
                (row[x_col], row[y_col]),
                fontsize=8,
                alpha=0.7,
            )

    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or y_col)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        buf.seek(0)

    return buf


def create_yearly_scoring_chart(
    data: pd.DataFrame,
    title: str = "Total Points by Manager Over Time",
    output_path: str = None,
) -> BytesIO:
    """Create a line chart showing total points for each manager by year.

    Args:
        data: DataFrame with columns: season, team_name, total_points
        title: Chart title
        output_path: Optional path to save the image

    Returns:
        BytesIO buffer containing the image
    """
    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(14, 8))

    # Get unique managers and assign colors
    managers = data["team_name"].unique()
    color_map = plt.cm.tab20(np.linspace(0, 1, len(managers)))

    for i, manager in enumerate(managers):
        manager_data = data[data["team_name"] == manager].sort_values("season")
        ax.plot(
            manager_data["season"],
            manager_data["total_points"],
            label=manager,
            marker="o",
            color=color_map[i],
            linewidth=2,
            markersize=6,
        )

    ax.set_xlabel("Season", fontsize=12)
    ax.set_ylabel("Total Points", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)

    # Legend outside the plot
    ax.legend(
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=9,
        framealpha=0.9,
    )

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        buf.seek(0)

    return buf
