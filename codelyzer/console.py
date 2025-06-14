"""
Console and display utilities for CodeLyzer.
Centralizes all console output, logging, progress bars, and rich display components.
"""
import functools
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Dict, Callable, TypeVar, cast

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich.box import Box
from rich.traceback import install as install_rich_traceback

from codelyzer.metrics import ProjectMetrics, ComplexityLevel
from codelyzer.config import LOG_FILENAME, DEBUG, LOG_FILENAME

# Install rich traceback handler for better exception visualization
install_rich_traceback()



# Configure the rich console for standard output
console = Console()

# Configure rich handler for console output
rich_handler = RichHandler(
    console=console,
    rich_tracebacks=True,
    markup=True,
    show_time=True,
    show_level=True,
    show_path=True
)

# Configure file handler for log file output
file_handler = logging.FileHandler(LOG_FILENAME, mode="w", encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[rich_handler, file_handler],
    format="%(message)s",  # The rich handler will handle the formatting for console
)

# Create dedicated logger for CodeLyzer
logger = logging.getLogger("codelyzer")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Function return type for decorator
F = TypeVar('F', bound=Callable[..., Any])

def debug_log(message: str) -> None:
    """Log a debug message if DEBUG mode is enabled.
    
    Args:
        message: The debug message to log
    """
    if DEBUG:
        logger.debug(message)

def debug(func: F) -> F:
    """Decorator to log function entry, exit, and execution time if DEBUG is True.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not DEBUG:
            return func(*args, **kwargs)
        
        # Log function entry with arguments
        arg_str = ", ".join([str(a) for a in args])
        kwarg_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        params = ", ".join(filter(None, [arg_str, kwarg_str]))
        logger.debug(f"ENTER: {func.__name__}({params})")
        
        # Track execution time
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"EXIT: {func.__name__} -> {result if result is not None else 'None'}")
            return result
        except Exception as e:
            logger.debug(f"ERROR in {func.__name__}: {str(e)}")
            raise
        finally:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"TIME: {func.__name__} took {execution_time:.4f}s")
    
    return cast(F, wrapper)

def set_log_level(level: int) -> None:
    """Set the log level for the codelyzer logger.
    
    Args:
        level: The log level to set (e.g., logging.DEBUG, logging.INFO)
    """
    logger.setLevel(level)
    logger.info(f"Log level set to {logging.getLevelName(level)}")

def get_log_file_path() -> Path:
    """Get the current log file path.
    
    Returns:
        Path object pointing to the current log file
    """
    return LOG_FILENAME

@debug
def create_summary_panel(metrics: ProjectMetrics) -> Panel:
    """Create a summary panel with project metrics."""
    summary_text = f"""
📊 **Project Overview**
• Files analyzed: {metrics.total_files:,}
• Lines of code: {metrics.total_loc:,}
• Source lines: {metrics.total_sloc:,}
• Comments: {metrics.total_comments:,}
• Blank lines: {metrics.total_blanks:,}

🏗️ **Code Structure**
• Classes: {metrics.total_classes:,}
• Functions: {metrics.total_functions:,}
• Methods: {metrics.total_methods:,}

📈 **Quality Metrics**
• Code quality: {metrics.code_quality_score:.1f}/100
• Maintainability: {metrics.maintainability_score:.1f}/100
• Analysis time: {metrics.analysis_duration:.2f}s
"""

    logger.info(f"Created summary panel with {metrics.total_files} files and {metrics.total_loc} lines")
    return Panel(
        Markdown(summary_text),
        title="📋 Analysis Summary",
        border_style="blue",
        padding=(1, 2),
        title_align="center",
        highlight=True
    )

@debug
def create_language_distribution_table(metrics: ProjectMetrics) -> Table:
    """Create a table showing language distribution."""
    table = Table(
        title="🌐 Language Distribution",
        box=box.ROUNDED,
        title_style="bold blue",
        border_style="cyan",
        highlight=True
    )
    table.add_column("Language", style="cyan", no_wrap=True)
    table.add_column("Files", justify="right", style="magenta")
    table.add_column("Percentage", justify="right", style="green")

    total_files = sum(metrics.languages.values())
    for language, count in sorted(metrics.languages.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_files) * 100 if total_files > 0 else 0
        table.add_row(
            language.title(),
            str(count),
            f"{percentage:.1f}%"
        )
    
    logger.info(f"Created language distribution table with {len(metrics.languages)} languages")
    return table

@debug
def create_complexity_table(metrics: ProjectMetrics) -> Table:
    """Create a table showing code complexity distribution."""
    table = Table(
        title="⚡ Complexity Distribution",
        box=box.ROUNDED,
        title_style="bold blue",
        border_style="cyan",
        highlight=True
    )
    table.add_column("Complexity Level", style="cyan")
    table.add_column("Files", justify="right", style="magenta")
    table.add_column("Percentage", justify="right", style="green")

    total_files = sum(metrics.complexity_distribution.values())

    for level in ComplexityLevel:
        # noinspection PyTypeChecker
        count = metrics.complexity_distribution.get(level, 0)
        percentage = (count / total_files) * 100 if total_files > 0 else 0

        # Color coding
        if level in [ComplexityLevel.TRIVIAL, ComplexityLevel.LOW]:
            style = "green"
        elif level == ComplexityLevel.MODERATE:
            style = "yellow"
        else:
            style = "red"

        table.add_row(
            level.replace('_', ' ').title(),
            f"[{style}]{count}[/{style}]",
            f"[{style}]{percentage:.1f}%[/{style}]"
        )
    
    logger.info(f"Created complexity table with distribution across {len(ComplexityLevel)} levels")
    return table

@debug
def create_table(title: str, box: Box, title_style: str, border_style: str, highlight: bool) -> Table:
    """Create a table with the given parameters."""
    logger.debug(f"Creating table with title: {title}")
    return Table(
        title=title,
        box=box,
        title_style=title_style,
        border_style=border_style,
        highlight=highlight
    )

@debug
def create_table_columns(table: Table, columns: Dict[str, Dict[str, Any]]) -> Table:
    """Update a table with the given columns."""
    logger.debug(f"Adding {len(columns)} columns to table")
    for column_name, column_config in columns.items():
        table.add_column(column_name, **column_config)
    return table

def _get_file_relative_path(file_path: str) -> str:
    """Get a readable relative path for display.
    
    Args:
        file_path: The absolute file path
        
    Returns:
        A simplified relative path for display
    """
    try:
        # Try relative path first
        relative_path = str(Path(file_path).relative_to(Path.cwd()))
    except ValueError:
        # If on a different drive, just use the basename or full path
        path_obj = Path(file_path)
        # Use parent directory + filename for better context
        if path_obj.parent.name:
            relative_path = str(Path(path_obj.parent.name) / path_obj.name)
        else:
            relative_path = path_obj.name
    
    debug_log(f"Resolved file path '{file_path}' to relative path '{relative_path}'")
    return relative_path

def _get_issue_style(issue_count: int) -> str:
    """Determine the style color based on issue count.
    
    Args:
        issue_count: Number of issues in the file
        
    Returns:
        Style color name
    """
    if issue_count == 0:
        return "green"
    elif issue_count < 3:
        return "yellow"
    else:
        return "red"

def _get_issue_display(issue_count: int, style: str) -> str:
    """Format the issue display with appropriate styling.
    
    Args:
        issue_count: Number of issues in the file
        style: Style color to use
        
    Returns:
        Formatted issue string
    """
    display_text = "✅" if issue_count == 0 else str(issue_count)
    return f"[{style}]{display_text}[/{style}]"

def _create_hotspots_table_columns() -> Dict[str, Dict[str, Any]]:
    """Define the columns for the hotspots table.
    
    Returns:
        Dictionary of column configurations
    """
    return {
        "file": {"style": "cyan", "max_width": 50},
        "lines": {"justify": "right", "style": "magenta"},
        "complexity": {"justify": "right", "style": "red"},
        "issues": {"justify": "right", "style": "yellow"}
    }

def _build_file_metrics_map(metrics: ProjectMetrics) -> Dict[str, Any]:
    """Create a mapping of file paths to their metrics for quick lookup.
    
    Args:
        metrics: Project metrics data
        
    Returns:
        Dictionary mapping file paths to FileMetrics objects
    """
    file_map = {fm.file_path: fm for fm in metrics.file_metrics}
    debug_log(f"Built file metrics map with {len(file_map)} entries")
    return file_map

@debug
def create_hotspots_table(metrics: ProjectMetrics) -> Table:
    """Create a table showing code hotspots (most complex files)."""
    table = create_table(
        title="🔥 Code Hotspots (Most Complex Files)",
        box=box.ROUNDED,
        title_style="bold blue",
        border_style="cyan",
        highlight=True
    )
    
    columns = _create_hotspots_table_columns()
    create_table_columns(table, columns)

    # Create a mapping of file paths to file metrics for quick lookup
    file_metrics_map = _build_file_metrics_map(metrics)

    # Loop through the most complex file paths and find their corresponding FileMetrics objects
    hotspot_count = min(10, len(metrics.most_complex_files))
    logger.info(f"Adding {hotspot_count} files to hotspots table")
    
    for file_path in metrics.most_complex_files[:10]:
        # Get the FileMetrics object for this file path
        file_metrics = file_metrics_map.get(file_path)

        if file_metrics:
            relative_path = _get_file_relative_path(file_metrics.file_path)
            issues = len(file_metrics.security_issues) + len(file_metrics.code_smells_list)
            issue_style = _get_issue_style(issues)

            table.add_row(
                relative_path,
                str(file_metrics.sloc),
                f"{file_metrics.complexity_score:.0f}",
                _get_issue_display(issues, issue_style)
            )

    return table

@debug
def create_dependencies_table(metrics: ProjectMetrics) -> Table:
    """Create a table showing top dependencies."""
    table = Table(
        title="📦 Top Dependencies",
        box=box.ROUNDED,
        title_style="bold blue",
        border_style="cyan",
        highlight=True
    )
    table.add_column("Module", style="cyan")
    table.add_column("Usage Count", justify="right", style="magenta")

    # Get top 15 dependencies
    top_deps = sorted(metrics.structure.dependencies.items(), key=lambda x: x[1], reverse=True)[:15]
    logger.info(f"Adding {len(top_deps)} dependencies to table")

    for module, count in top_deps:
        table.add_row(module, str(count))

    return table

@debug
def create_finding_files_progress_bar() -> Progress:
    """Create undetermind progress bar for finding files."""
    logger.debug("Creating progress bar for file discovery")
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Finding files...", justify="right"),
        console=console
    )

@debug
def create_analysis_progress_bar() -> Progress:
    """Create a standardized progress bar for analysis operations."""
    logger.debug("Creating progress bar for analysis")
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Processing...", justify="right"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]", justify="right"),
        "•",
        TimeElapsedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console
    )

@debug
def create_and_display_layout(metrics: ProjectMetrics) -> None:
    """Create and display the layout with all metric tables."""
    logger.info("Creating and displaying layout with metric tables")
    layout = Layout()
    layout.split_column(
        Layout(name="top"),
        Layout(name="bottom")
    )

    layout["top"].split_row(
        Layout(create_language_distribution_table(metrics), name="languages"),
        Layout(create_complexity_table(metrics), name="complexity")
    )

    layout["bottom"].split_row(
        Layout(create_hotspots_table(metrics), name="hotspots"),
        Layout(create_dependencies_table(metrics), name="dependencies")
    )

    console.print(layout)

@debug
def display_initial_info(project_path: Path, exclude: List[str], include_tests: bool) -> None:
    """Display initial information about the analysis."""
    logger.info(f"Starting analysis of project: {project_path}")
    logger.info(f"Exclusions: {', '.join(exclude) if exclude else 'None'}")
    logger.info(f"Including tests: {include_tests}")
    
    console.print(Panel.fit(
        f"🔍 [bold blue]Advanced Codebase Analysis[/bold blue]\n"
        f"📁 Project: [cyan]{project_path.name}[/cyan]\n"
        f"📂 Path: [dim]{project_path}[/dim]",
        border_style="blue"
    ))

    if exclude:
        console.print(f"[yellow]📁 Excluding directories:[/yellow] {', '.join(exclude)}")

    if include_tests:
        console.print("[yellow]🧪 Including test directories[/yellow]")

@debug
def display_final_summary(metrics: ProjectMetrics) -> None:
    """Display the final analysis summary."""
    logger.info("Analysis complete")
    logger.info(f"Code Quality Score: {metrics.code_quality_score:.1f}/100")
    logger.info(f"Maintainability Score: {metrics.maintainability_score:.1f}/100")
    logger.info(f"Analysis Duration: {metrics.analysis_duration:.2f}s")
    logger.info(f"Log file saved to: {LOG_FILENAME}")
    
    console.rule("[bold green]🎉 Analysis Complete")

    quality_emoji = "🟢" if metrics.code_quality_score >= 80 else "🟡" if metrics.code_quality_score >= 60 else "🔴"
    maintainability_emoji = "🟢" if metrics.maintainability_score >= 80 else "🟡" if metrics.maintainability_score >= 60 else "🔴"

    console.print(f"""
[bold]📈 Final Assessment:[/bold]
{quality_emoji} Code Quality: {metrics.code_quality_score:.1f}/100
{maintainability_emoji} Maintainability: {metrics.maintainability_score:.1f}/100
⏱️  Analysis completed in {metrics.analysis_duration:.2f} seconds
🎯 Focus on the {len(metrics.most_complex_files)} most complex files for maximum impact
📝 Log file: {LOG_FILENAME}
""")

@debug
def display_verbose_info(metrics: ProjectMetrics) -> None:
    """Display additional verbose information."""
    logger.info("Displaying verbose analysis information")
    console.rule("[bold blue]📊 Detailed Analysis")

    # File size distribution
    size_table = Table(title="📏 File Size Distribution", box=box.ROUNDED)
    size_table.add_column("Size Range", style="cyan")
    size_table.add_column("Files", justify="right", style="magenta")

    size_ranges = [(0, 100), (100, 500), (500, 1000), (1000, 5000), (5000, float('inf'))]
    size_labels = ["< 100 lines", "100-500 lines", "500-1K lines", "1K-5K lines", "> 5K lines"]

    for (min_size, max_size), label in zip(size_ranges, size_labels):
        count = sum(1 for f in metrics.file_metrics
                    if min_size <= f.sloc < max_size)
        size_table.add_row(label, str(count))

    console.print(size_table)
    console.print()

    display_security_issues(metrics)

@debug
def display_security_issues(metrics: ProjectMetrics) -> None:
    """Display security issues if any exist."""
    from collections import Counter

    security_issues = sum(len(f.security_issues) for f in metrics.file_metrics)
    logger.info(f"Found {security_issues} security issues")

    if any(f.security_issues for f in metrics.file_metrics):
        security_table = Table(title="🔒 Security Issues", box=box.ROUNDED)
        security_table.add_column("Issue Type", style="red")
        security_table.add_column("Files Affected", justify="right", style="magenta")

        security_counts = Counter()
        for file_metrics in metrics.file_metrics:
            for issue in file_metrics.security_issues:
                issue_type = issue.get('type', 'unknown')
                security_counts[issue_type] += 1

        for issue_type, count in security_counts.most_common():
            security_table.add_row(issue_type.replace('_', ' ').title(), str(count))

        console.print(security_table)
        console.print()
