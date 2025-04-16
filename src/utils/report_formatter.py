# src/utils/report_formatter.py
"""Report formatter for generating terminal-based reports using Rich."""

import time
from collections import Counter
from typing import Any, List, Optional, Dict, Tuple

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.domain.enums.search_status import SearchStatus
from src.domain.enums.search_strategy_type import SearchStrategyType
from src.domain.models.config import Config
from src.domain.models.search_result import SearchResult

# Emojis for visual clarity
EMOJI = {
    "FOUND": "✅",
    "NOT_FOUND": "❌",
    "REJECTED": "⚠️", # Warning sign for rejected
    "SKIPPED": "⏭️", # Skip track symbol
    "CONFIG": "⚙️",
    "THRESHOLDS": "📏",
    "STRATEGIES": "🧭",
    "API": "☁️",
    "SUMMARY": "📊",
    "STRATEGY_FLOW": "➡️",
    "SUGGESTIONS": "💡",
}

# Colors for different statuses
STATUS_COLORS = {
    SearchStatus.FOUND: "green",
    SearchStatus.NOT_FOUND: "red",
    SearchStatus.REJECTED: "yellow",
    SearchStatus.SKIPPED: "dim", # Dim for skipped
}

# Updated strategy names and status mapping
STRATEGY_NAMES: Dict[str, str] = {
    SearchStrategyType.IDENTIFIER.value: "Identifier (DOI/PMID)",
    SearchStrategyType.TITLE_AUTHORS_YEAR.value: "Title + Authors + Year",
    SearchStrategyType.TITLE_AUTHORS.value: "Title + Authors",
    SearchStrategyType.TITLE_YEAR.value: "Title + Year",
    SearchStrategyType.TITLE_ONLY.value: "Title Only",
}

STRATEGY_STATUS: Dict[str, Tuple[str, str]] = {
    "found": (EMOJI["FOUND"], "MATCH FOUND!"),
    "rejected": (EMOJI["REJECTED"], "Rejected (Low Similarity)"),
    "not_found": (EMOJI["NOT_FOUND"], "No Match Found"),
    "error": ("🔥", "API/Exec Error"), # Fire for error
    "skipped": (EMOJI["SKIPPED"], "Skipped (Not Supported/Needed)"),
    "not_attempted": ("⚪", "Not Attempted"), # White circle for not attempted
}

class ReportFormatter:
    """Formats and prints reports to the console using Rich."""

    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        self.results: List[SearchResult] = []
        self.start_time: Optional[float] = None # Set when processing starts

    def add_results(self, results: List[SearchResult]) -> None:
        self.results = results

    def set_start_time(self, start_time: float) -> None:
        self.start_time = start_time

    def generate_report(self) -> None:
        """Generate the complete report."""
        self.console.print("\n")
        self.generate_config_panel()
        self.console.print("\n")
        self.generate_study_panels()
        self.console.print("\n")
        self.generate_statistics_panel()
        self.console.print("\n")

    def render(self) -> None:
        """Render the report to the console."""
        if self.start_time is None:
             self.start_time = time.perf_counter() # Fallback if not set
        self.generate_report()

    def generate_config_panel(self) -> None:
        """Generate and print the configuration panel."""
        panel_title = f"{EMOJI['CONFIG']} OpenAlex Search Configuration"

        # Thresholds
        thresholds_content = [
            f"• Title Similarity: {self.config.title_similarity_threshold:.2f}",
            f"• Author Similarity: {self.config.author_similarity_threshold:.2f}",
        ]
        # Add specific thresholds if they exist in config
        # (Using getattr for safety if these aren't added to Config model)
        # if hasattr(self.config, 'title_year_similarity_threshold'):
        #      thresholds_content.append(f"• Title+Year Threshold: {self.config.title_year_similarity_threshold:.2f}")
        # if hasattr(self.config, 'title_only_similarity_threshold'):
        #      thresholds_content.append(f"• Title Only Threshold: {self.config.title_only_similarity_threshold:.2f}")
        thresholds_section = f"{EMOJI['THRESHOLDS']} Similarity Thresholds:\n" + "\n".join(thresholds_content)

        # Strategies
        strategies_title = f"{EMOJI['STRATEGIES']} Active Search Strategies (Priority Order):"
        strategies_content = []
        # Use the updated STRATEGY_NAMES
        active_strategies = [s.value for s in SearchStrategyType if s.value not in self.config.disable_strategies]
        sorted_strategies = sorted(active_strategies, key=lambda s: SearchStrategyType(s).priority)

        for i, strategy_key in enumerate(sorted_strategies):
             strategy_name = STRATEGY_NAMES.get(strategy_key, strategy_key.replace("_", " ").title())
             strategies_content.append(f"{i+1}. {strategy_name}")

        # Show disabled strategies clearly
        disabled_strats = [STRATEGY_NAMES.get(s, s) for s in self.config.disable_strategies if s in STRATEGY_NAMES]
        disabled_section = ""
        if disabled_strats:
             disabled_section = f"\n\n[dim]Disabled Strategies:[/dim] {', '.join(disabled_strats)}"

        strategies_section = f"{strategies_title}\n" + "\n".join(strategies_content) + disabled_section


        # API Settings
        api_title = f"{EMOJI['API']} API Settings:"
        api_content = [
            f"• API Email: {self.format_field_value(self.config.openalex_email)}",
            f"• Max Retries: {self.config.max_retries}",
            f"• Retry Backoff: {self.config.retry_backoff_factor}",
            f"• Retry Codes: {self.format_field_value(self.config.retry_http_codes)}",
            f"• Concurrency: {self.config.concurrency}",
        ]
        api_section = f"{api_title}\n" + "\n".join(api_content)

        panel_content = f"{thresholds_section}\n\n{strategies_section}\n\n{api_section}"
        panel = Panel(panel_content, title=panel_title, title_align="left", border_style="blue")
        self.console.print(panel)

    def generate_study_panels(self) -> None:
        """Generate and print panels for each study result."""
        if not self.results:
            self.console.print("[yellow]No results to display.[/yellow]")
            return
        for result in self.results:
            self.generate_study_panel(result)

    def generate_study_panel(self, result: SearchResult) -> None:
        """Generate and print a panel for a single study result."""
        if not result.study_id:
            logger.warning("Search result missing study_id, skipping panel generation.")
            return

        status_emoji = EMOJI.get(result.status.value.upper(), "❓")
        panel_title = f"{status_emoji} {result.status.value.upper()}: {result.study_id}"
        border_color = STATUS_COLORS.get(result.status, "white")

        content_sections = []

        # Status line
        status_text = f"[bold {border_color}]Status: {result.status.value}[/bold {border_color}]"
        if result.strategy:
            strategy_display_name = STRATEGY_NAMES.get(result.strategy, result.strategy)
            status_text += f" (via [cyan]{strategy_display_name}[/cyan])"
        content_sections.append(status_text)

        # Original Reference (shown for NOT_FOUND, REJECTED, SKIPPED)
        if result.status != SearchStatus.FOUND and result.original_reference:
             ref_section = "[bold]Original Reference:[/bold]"
             ref_details = []
             ref_data = result.original_reference
             if ref_data.get("title"): ref_details.append(f"  Title: {self.truncate_text(ref_data['title'])}")
             if ref_data.get("authors"): ref_details.append(f"  Authors: {self.format_field_value(ref_data['authors'])}")
             if ref_data.get("year"): ref_details.append(f"  Year: {ref_data['year']}")
             if ref_data.get("journal"): ref_details.append(f"  Journal: {ref_data['journal']}")
             if ref_data.get("doi"): ref_details.append(f"  DOI: {ref_data['doi']}")
             if ref_data.get("pmid"): ref_details.append(f"  PMID: {ref_data['pmid']}")
             if ref_details:
                  content_sections.append(f"{ref_section}\n" + "\n".join(ref_details))
             elif result.status == SearchStatus.SKIPPED:
                  content_sections.append("[yellow]Reason: Insufficient data for searching.[/yellow]")


        # Publication Details (for FOUND)
        if result.status == SearchStatus.FOUND:
            pub_section = "[bold green]Found Publication:[/bold green]"
            pub_details = []
            if result.openalex_id: pub_details.append(f"  OpenAlex ID: {result.openalex_id}")
            if result.title: pub_details.append(f"  Title: {self.truncate_text(result.title)}")
            if result.journal: pub_details.append(f"  Journal: {result.journal}")
            if result.year: pub_details.append(f"  Year: {result.year}")
            if result.doi: pub_details.append(f"  DOI: {result.doi}")
            if result.open_access is not None: pub_details.append(f"  Open Access: {self.format_field_value(result.open_access)}")
            if result.citation_count is not None: pub_details.append(f"  Citations: {result.citation_count}")
            if result.pdf_url: pub_details.append(f"  PDF URL: {result.pdf_url}")
            else:  pub_details.append("  PDF URL: [dim]Not available[/dim]")
            if pub_details:
                 content_sections.append(f"{pub_section}\n" + "\n".join(pub_details))

            # Search Details (for FOUND)
            if result.search_details:
                 sd_section = "[bold]Search Details:[/bold]"
                 sd_details = []
                 sd_data = result.search_details
                 # Don't display strategy again if already shown
                 # if sd_data.get("strategy"): sd_details.append(f"  Strategy: {sd_data['strategy']}")
                 if sd_data.get("query_type"): sd_details.append(f"  Query Type: {sd_data['query_type']}")
                 if sd_data.get("search_term"): sd_details.append(f"  Search Term: '{self.truncate_text(sd_data['search_term'])}'")
                 # Display similarity scores if present
                 scores_text = []
                 if 'title_similarity' in sd_data: scores_text.append(f"Title Sim: {sd_data['title_similarity']:.2f}")
                 if 'authors_similarity' in sd_data: scores_text.append(f"Author Sim: {sd_data['authors_similarity']:.2f}")
                 if scores_text: sd_details.append(f"  Similarity: {', '.join(scores_text)}")

                 if sd_details:
                      content_sections.append(f"{sd_section}\n" + "\n".join(sd_details))

        # Strategy Flow Table (for all except SKIPPED)
        if result.status != SearchStatus.SKIPPED and result.search_attempts:
            strategy_table = self.generate_strategy_flow_table(result)
            content_sections.append(strategy_table) # Add table object directly

        # Improvement Suggestions (for NOT_FOUND, REJECTED)
        if result.status in [SearchStatus.NOT_FOUND, SearchStatus.REJECTED]:
             suggestions = self.generate_improvement_suggestions(result)
             if suggestions:
                 sug_section = f"[bold {border_color}]{EMOJI['SUGGESTIONS']} Improvement Suggestions:[/bold {border_color}]"
                 sug_list = "\n".join([f"• {s}" for s in suggestions])
                 content_sections.append(f"{sug_section}\n{sug_list}")


        # Join sections with double newlines
        panel_content = "\n\n".join(str(section) for section in content_sections) # Ensure all are strings

        # Create and print panel
        panel = Panel(
            panel_content,
            title=panel_title,
            title_align="left",
            border_style=border_color,
            padding=(1, 2)
        )
        self.console.print(panel)

    def generate_strategy_flow_table(self, result: SearchResult) -> Table:
        """Generate a table showing the flow of strategies for a result."""
        table = Table(
            title=f"{EMOJI['STRATEGY_FLOW']} Strategy Flow",
            show_header=False, box=None, padding=0, expand=True
        )
        table.add_column("Strategy Name", style="dim", width=25)
        table.add_column("Status")

        attempted_strategies_status: Dict[str, Tuple[str, str]] = {}
        final_strategy_priority = float('inf')
        if result.strategy:
             final_strategy_priority = SearchStrategyType(result.strategy).priority


        if result.search_attempts:
            for attempt in result.search_attempts:
                 strategy_key = attempt.get("strategy")
                 if not strategy_key: continue

                 status_tuple: Tuple[str, str]
                 error = attempt.get("error")

                 if result.status == SearchStatus.FOUND and result.strategy == strategy_key:
                      status_tuple = STRATEGY_STATUS["found"]
                 elif error:
                     if "similarity below threshold" in error:
                         status_tuple = STRATEGY_STATUS["rejected"]
                     elif "not found" in error.lower():
                          status_tuple = STRATEGY_STATUS["not_found"]
                     else: # Other errors
                          status_tuple = STRATEGY_STATUS["error"]
                 else: # Attempted but didn't lead to final match / error
                      status_tuple = STRATEGY_STATUS["skipped"]

                 attempted_strategies_status[strategy_key] = status_tuple

        # Iterate through all possible strategies in priority order
        all_strategy_keys = sorted(STRATEGY_NAMES.keys(), key=lambda s: SearchStrategyType(s).priority)

        for strategy_key in all_strategy_keys:
            strategy_name = STRATEGY_NAMES.get(strategy_key, strategy_key)
            current_priority = SearchStrategyType(strategy_key).priority

            if strategy_key in attempted_strategies_status:
                 status_icon, status_text = attempted_strategies_status[strategy_key]
                 # Shorten error message if needed
                 if status_icon == STRATEGY_STATUS["error"][0]:
                      error_detail = next((a.get("error") for a in result.search_attempts if a.get("strategy") == strategy_key), "")
                      status_text = f"Error: {self.truncate_text(error_detail, 30)}"

            elif result.status == SearchStatus.FOUND and current_priority > final_strategy_priority:
                  status_icon, status_text = STRATEGY_STATUS["not_attempted"]
                  status_text += " (Match Found Earlier)"
            elif result.status != SearchStatus.FOUND and strategy_key not in attempted_strategies_status:
                 # If not found and not attempted, assume not supported or disabled
                 status_icon, status_text = STRATEGY_STATUS["not_attempted"]
                 status_text += " (Not Supported/Needed/Disabled)"
            else:
                 # Fallback for unhandled states
                 status_icon, status_text = "❓", "Unknown State"


            table.add_row(f"{strategy_name}", f"{status_icon} {status_text}")

        return table

    def generate_statistics_panel(self) -> None:
        """Generate and print summary statistics panel."""
        panel_title = f"{EMOJI['SUMMARY']} Summary Statistics"

        total_studies = len(self.results)
        if total_studies == 0:
            self.console.print(Panel("No studies processed.", title=panel_title, border_style="yellow"))
            return

        status_counts = Counter(result.status for result in self.results)
        found_count = status_counts.get(SearchStatus.FOUND, 0)
        success_rate = (found_count / total_studies * 100) if total_studies > 0 else 0.0

        with_pdf_url = sum(1 for r in self.results if r.status == SearchStatus.FOUND and r.pdf_url)
        open_access = sum(1 for r in self.results if r.status == SearchStatus.FOUND and r.open_access)
        with_doi = sum(1 for r in self.results if r.status == SearchStatus.FOUND and r.doi)

        processing_time = (time.perf_counter() - self.start_time) if self.start_time is not None else -1.0
        time_str = f"{processing_time:.2f}s" if processing_time >= 0 else "N/A"

        stats_content = [
            f"Total Studies Processed: {total_studies}",
            f"Success Rate: {success_rate:.1f}%",
            f"  - Found: {found_count} ({success_rate:.1f}%)",
            f"  - Not Found: {status_counts.get(SearchStatus.NOT_FOUND, 0)} ({status_counts.get(SearchStatus.NOT_FOUND, 0)/total_studies*100:.1f}%)",
            f"  - Rejected: {status_counts.get(SearchStatus.REJECTED, 0)} ({status_counts.get(SearchStatus.REJECTED, 0)/total_studies*100:.1f}%)",
            f"  - Skipped: {status_counts.get(SearchStatus.SKIPPED, 0)} ({status_counts.get(SearchStatus.SKIPPED, 0)/total_studies*100:.1f}%)",
            f"Found w/ PDF URL: {with_pdf_url}",
            f"Found w/ Open Access: {open_access}",
            f"Found w/ DOI: {with_doi}",
            f"Processing Time: {time_str}",
        ]

        panel_content = "\n".join(stats_content)
        panel = Panel(panel_content, title=panel_title, title_align="left", border_style="green")
        self.console.print(panel)

    def generate_improvement_suggestions(self, result: SearchResult) -> List[str]:
        """Generate improvement suggestions for a result."""
        suggestions = []
        if result.status == SearchStatus.SKIPPED:
             suggestions.append("Provide minimal data (Title or DOI/PMID) for searching.")
             return suggestions

        if result.status in [SearchStatus.NOT_FOUND, SearchStatus.REJECTED]:
            # Check if crucial identifiers were missing
            missing_ids = []
            if not result.original_reference or not result.original_reference.get('doi'):
                 missing_ids.append("DOI")
            if not result.original_reference or not result.original_reference.get('pmid'):
                 missing_ids.append("PMID")
            if missing_ids:
                 suggestions.append(f"Consider adding missing identifiers ({', '.join(missing_ids)}) for higher precision.")

            # Analyze rejection reasons
            if result.status == SearchStatus.REJECTED and result.search_attempts:
                 last_error = result.search_attempts[-1].get("error", "") if result.search_attempts else ""
                 if "title similarity" in last_error or "similarity below threshold" in last_error:
                      suggestions.append(f"Review title accuracy or consider adjusting title threshold (current base: {self.config.title_similarity_threshold:.2f}).")
                 if "author similarity" in last_error or "similarity below threshold" in last_error:
                      suggestions.append(f"Review author list/format or consider adjusting author threshold (current: {self.config.author_similarity_threshold:.2f}).")
                 if "year mismatch" in last_error:
                     suggestions.append("Verify publication year accuracy.")

            # Generic suggestion if still not found
            if not suggestions and result.status == SearchStatus.NOT_FOUND:
                 suggestions.append("Verify reference details or try manual search in OpenAlex.")

        return suggestions


    def truncate_text(self, text: Optional[str], max_length: int = 60) -> str:
        """Truncate text to a maximum length."""
        if not text: return ""
        return (text[:max_length-3] + "...") if len(text) > max_length else text

    def format_field_value(self, value: Any) -> str:
        """Format a field value for display."""
        if value is None: return "[dim]Not set[/dim]"
        if isinstance(value, bool): return "[green]Yes[/green]" if value else "[red]No[/red]"
        if isinstance(value, list):
            if not value: return "[dim]None[/dim]"
            # Truncate long lists
            display_items = [str(v) for v in value[:3]]
            if len(value) > 3: display_items.append("...")
            return ", ".join(display_items)
        return str(value)
