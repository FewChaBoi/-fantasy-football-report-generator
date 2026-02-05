"""Table formatting utilities for PDF reports."""

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle


# Exciting sports color palette - bold and vibrant
COLORS = {
    'primary': colors.Color(0.1, 0.1, 0.15),         # Rich dark charcoal
    'primary_light': colors.Color(0.2, 0.2, 0.25),   # Lighter charcoal
    'accent': colors.Color(1.0, 0.5, 0.0),           # Vibrant orange
    'accent_gold': colors.Color(1.0, 0.84, 0.0),     # Bright gold
    'accent_green': colors.Color(0.0, 0.8, 0.4),     # Victory green
    'accent_red': colors.Color(0.9, 0.2, 0.2),       # Fire red
    'row_alt': colors.Color(0.97, 0.97, 0.97),       # Light gray
    'row_alt2': colors.Color(1.0, 0.98, 0.95),       # Warm white
    'text_dark': colors.Color(0.15, 0.15, 0.15),     # Near black
    'text_light': colors.white,
    'border': colors.Color(0.85, 0.85, 0.85),        # Light border
    'border_header': colors.Color(0.1, 0.1, 0.1),    # Dark header border
    'gradient_top': colors.Color(0.15, 0.15, 0.2),   # Gradient dark
    'gradient_bot': colors.Color(0.25, 0.25, 0.3),   # Gradient light
}


def format_dataframe_for_pdf(
    df: pd.DataFrame,
    columns: list = None,
    column_names: dict = None,
    number_format: dict = None,
    max_rows: int = None,
) -> list:
    """Convert a DataFrame to a list of lists for PDF table.

    Args:
        df: DataFrame to convert
        columns: List of columns to include (in order)
        column_names: Dict mapping column names to display names
        number_format: Dict mapping column names to format strings (e.g., "{:.2f}")
        max_rows: Maximum number of rows to include

    Returns:
        List of lists suitable for reportlab Table
    """
    if df.empty:
        return [[]]

    # Select and order columns
    if columns:
        df = df[[c for c in columns if c in df.columns]]

    if max_rows:
        df = df.head(max_rows)

    df = df.copy()

    # Format specified numbers first (before renaming)
    if number_format:
        for col, fmt in number_format.items():
            if col in df.columns:
                df[col] = df[col].apply(lambda x: fmt.format(x) if pd.notna(x) else "")

    # Auto-format any remaining float columns to 2 decimal places
    for col in df.columns:
        if df[col].dtype in ['float64', 'float32'] and col not in (number_format or {}):
            df[col] = df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")

    # Rename columns (after formatting)
    if column_names:
        df = df.rename(columns=column_names)

    # Convert to list of lists
    data = [df.columns.tolist()]
    for _, row in df.iterrows():
        data.append([str(v) if pd.notna(v) else "" for v in row.values])

    return data


def create_styled_table(
    data: list,
    col_widths: list = None,
    header_color: tuple = None,
    alternate_row_color: tuple = None,
    font_size: int = 10,
    header_font_size: int = 11,
    style_type: str = "professional",
) -> Table:
    """Create a styled reportlab Table with professional business styling.

    Args:
        data: List of lists (first row is header)
        col_widths: List of column widths in inches
        header_color: RGB tuple for header background (overrides style_type)
        alternate_row_color: RGB tuple for alternating rows (overrides style_type)
        font_size: Body font size
        header_font_size: Header font size
        style_type: "professional", "minimal", or "accent"

    Returns:
        Styled reportlab Table object
    """
    if not data or not data[0]:
        return None

    # Calculate column widths if not provided
    if col_widths is None:
        num_cols = len(data[0])
        col_widths = [1.2 * inch] * num_cols

    table = Table(data, colWidths=col_widths)

    # Select color scheme
    if header_color:
        hdr_bg = colors.Color(*header_color)
    else:
        hdr_bg = COLORS['primary']

    if alternate_row_color:
        alt_bg = colors.Color(*alternate_row_color)
    else:
        alt_bg = COLORS['row_alt']

    # Build exciting sports-style with even headers
    style = [
        # Header styling - bold dark with vibrant accent
        ("BACKGROUND", (0, 0), (-1, 0), hdr_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS['text_light']),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("LEFTPADDING", (0, 0), (-1, 0), 3),
        ("RIGHTPADDING", (0, 0), (-1, 0), 3),

        # Header bottom accent line - vibrant orange
        ("LINEBELOW", (0, 0), (-1, 0), 3, COLORS['accent']),

        # Body styling
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 1), (-1, -1), COLORS['text_dark']),
        ("ALIGN", (0, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 1), (-1, -1), 3),
        ("RIGHTPADDING", (0, 1), (-1, -1), 3),

        # Left align first column (usually names)
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("LEFTPADDING", (0, 1), (0, -1), 5),

        # Clean borders
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, COLORS['border']),
        ("LINEBELOW", (0, -1), (-1, -1), 2, COLORS['accent']),

        # Bold outer frame
        ("BOX", (0, 0), (-1, -1), 2, COLORS['primary']),
    ]

    # Add alternating row colors for better readability
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), alt_bg))
        else:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.white))

    table.setStyle(TableStyle(style))
    return table


def create_compact_table(
    data: list,
    col_widths: list = None,
    font_size: int = 9,
) -> Table:
    """Create a compact table for dense data with professional styling.

    Args:
        data: List of lists (first row is header)
        col_widths: List of column widths in inches
        font_size: Font size

    Returns:
        Compact styled Table object
    """
    if not data or not data[0]:
        return None

    if col_widths is None:
        num_cols = len(data[0])
        col_widths = [0.9 * inch] * num_cols

    table = Table(data, colWidths=col_widths)

    style = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), COLORS['primary']),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS['text_light']),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), font_size),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 2, COLORS['accent']),

        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 1), (-1, -1), COLORS['text_dark']),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),

        # Borders
        ("BOX", (0, 0), (-1, -1), 1, COLORS['primary']),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, COLORS['border']),
    ]

    # Alternating rows
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), COLORS['row_alt']))

    table.setStyle(TableStyle(style))
    return table


def create_h2h_matrix_table(
    h2h_matrix: pd.DataFrame,
    cell_width: float = 0.55,
) -> Table:
    """Create a head-to-head matrix table with professional styling.

    Args:
        h2h_matrix: H2H matrix DataFrame from get_h2h_matrix
        cell_width: Width of each cell in inches

    Returns:
        Styled H2H matrix Table
    """
    if h2h_matrix.empty:
        return None

    # Add row labels
    data = [[""] + list(h2h_matrix.columns)]
    for team_name, row in h2h_matrix.iterrows():
        data.append([team_name] + list(row.values))

    num_cols = len(data[0])
    col_widths = [1.2 * inch] + [cell_width * inch] * (num_cols - 1)

    table = Table(data, colWidths=col_widths)

    style = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), COLORS['primary']),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS['text_light']),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),

        # First column (team names)
        ("BACKGROUND", (0, 1), (0, -1), COLORS['primary']),
        ("TEXTCOLOR", (0, 1), (0, -1), COLORS['text_light']),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (0, -1), 9),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("LEFTPADDING", (0, 1), (0, -1), 6),

        # Body cells
        ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (1, 1), (-1, -1), 9),
        ("TEXTCOLOR", (1, 1), (-1, -1), COLORS['text_dark']),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),

        # Borders - vibrant accent
        ("BOX", (0, 0), (-1, -1), 2, COLORS['primary']),
        ("LINEBELOW", (0, 0), (-1, 0), 3, COLORS['accent']),
        ("LINEAFTER", (0, 0), (0, -1), 3, COLORS['accent']),
        ("INNERGRID", (1, 1), (-1, -1), 0.5, COLORS['border']),
    ]

    # Highlight diagonal with gold accent
    for i in range(1, len(data)):
        style.append(("BACKGROUND", (i, i), (i, i), colors.Color(1.0, 0.9, 0.6)))

    # Alternating row backgrounds for body
    for i in range(1, len(data)):
        if i % 2 == 0:
            for j in range(1, num_cols):
                if i != j:  # Don't override diagonal
                    style.append(("BACKGROUND", (j, i), (j, i), COLORS['row_alt']))

    table.setStyle(TableStyle(style))
    return table


def format_currency(value: float) -> str:
    """Format a number as currency."""
    return f"${value:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a number as percentage."""
    return f"{value * 100:.{decimals}f}%"


def format_record(wins: int, losses: int, ties: int = 0) -> str:
    """Format a win-loss-tie record."""
    if ties:
        return f"{wins}-{losses}-{ties}"
    return f"{wins}-{losses}"
