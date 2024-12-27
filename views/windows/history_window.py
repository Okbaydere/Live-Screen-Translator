import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional, Protocol

import customtkinter as ctk
import pyperclip
from CTkMessagebox import CTkMessagebox

from models.translation_model import TranslationEntry

# Constants
CHUNK_SIZE = 20
DEBOUNCE_DELAY = 300
PREVIEW_LENGTH = 50
DATE_FILTER_OPTIONS = ["All Time", "Today", "Last 7 Days", "Last 30 Days"]
DEFAULT_ENGINE = "All Engines"


class HistoryWindowProtocol(Protocol):
    """Protocol defining the interface for history window callbacks"""

    def on_close(self) -> None: ...
    def clear_history(self) -> None: ...
    def on_copy_text(self, text: str) -> None: ...
    def on_filter_change(self, filter_type: str, value: str) -> None: ...


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, controller: HistoryWindowProtocol):
        super().__init__(parent)

        self.controller = controller
        self.entries: List[TranslationEntry] = []
        self.filtered_entries: List[TranslationEntry] = []
        self._search_after_id: Optional[str] = None
        self._stats: Dict = {}

        # Create main container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        # Create UI components
        self._create_stats_panel()
        self._create_filter_panel()
        self._create_list_and_detail_view()

        # Configure window behavior
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

        # Initialize empty state
        self._init_empty_stats()

    def _init_empty_stats(self) -> None:
        """Initialize empty statistics"""
        self.update_stats(
            {
                "total_entries": 0,
                "unique_sources": 0,
                "unique_targets": 0,
                "engines_used": [],
                "most_used_engine": None,
                "engine_usage": {},
            }
        )

    def load_entries(self, entries: List[TranslationEntry]) -> None:
        """Load history entries with error handling"""
        try:
            self.entries = entries
            self.filtered_entries = entries.copy()

            # Pre-calculate stats
            self._calculate_stats()

            # Load entries in chunks
            self.after(10, self._load_entries_chunk, 0, CHUNK_SIZE)

        except Exception as e:
            logging.error(f"Error loading entries: {e}")
            self.show_error("Error", "Failed to load history entries")

    def _calculate_stats(self):
        """Pre-calculate statistics"""
        if not self.entries:
            self._stats = {
                "total_entries": 0,
                "unique_sources": 0,
                "unique_targets": 0,
                "engines_used": [],
                "most_used_engine": None,
                "engine_usage": {},
            }
            return

        engines_count: dict[str, int] = {}
        sources = set()
        targets = set()

        for entry in self.entries:
            engines_count[entry.translation_engine] = (
                engines_count.get(entry.translation_engine, 0) + 1
            )
            sources.add(entry.source_lang)
            targets.add(entry.target_lang)

        most_used_engine = (
            max(engines_count.items(), key=lambda x: x[1])[0]
            if engines_count
            else None
        )

        self._stats = {
            "total_entries": len(self.entries),
            "unique_sources": len(sources),
            "unique_targets": len(targets),
            "engines_used": list(engines_count.keys()),
            "most_used_engine": most_used_engine,
            "engine_usage": engines_count,
        }

        self.update_stats(self._stats)

    def _load_entries_chunk(self, start: int, chunk_size: int):
        """Load entries in chunks to prevent UI freezing"""
        end = min(start + chunk_size, len(self.filtered_entries))

        # Clear widgets if this is the first chunk
        if start == 0:
            for widget in self.history_frame.winfo_children():
                widget.destroy()

        # Create widgets for this chunk
        for entry in self.filtered_entries[start:end]:
            self._create_entry_widget(entry)

        # Schedule next chunk if needed
        if end < len(self.filtered_entries):
            self.after(10, self._load_entries_chunk, end, chunk_size)
        else:
            # Update engine options after all entries are loaded
            self._update_engine_options()

    def update_stats(self, stats: dict):
        """Update statistics display"""
        self.total_label.configure(
            text=f"Total Entries: {
                stats['total_entries']}"
        )
        self.sources_label.configure(
            text=f"Unique Source Languages: {
                stats['unique_sources']}"
        )
        self.targets_label.configure(
            text=f"Unique Target Languages: {
                stats['unique_targets']}"
        )

        if stats["most_used_engine"]:
            engine_text = f"Most Used Engine: {stats['most_used_engine']}"
            if stats["engine_usage"]:
                usage = stats["engine_usage"][stats["most_used_engine"]]
                engine_text += f" ({usage} times)"
            self.engine_label.configure(text=engine_text)
        else:
            self.engine_label.configure(text="No translations yet")

    def _create_stats_panel(self):
        """Create statistics panel"""
        stats_frame = ctk.CTkFrame(self.container)
        stats_frame.pack(fill="x", padx=5, pady=5)

        # Toast label for notifications
        self.toast_label = ctk.CTkLabel(
            stats_frame, text="", text_color="gray"
        )
        self.toast_label.pack(anchor="w", padx=5, pady=2)

        self.total_label = ctk.CTkLabel(stats_frame, text="Total Entries: 0")
        self.total_label.pack(anchor="w", padx=5, pady=2)

        self.sources_label = ctk.CTkLabel(
            stats_frame, text="Unique Source Languages: 0"
        )
        self.sources_label.pack(anchor="w", padx=5, pady=2)

        self.targets_label = ctk.CTkLabel(
            stats_frame, text="Unique Target Languages: 0"
        )
        self.targets_label.pack(anchor="w", padx=5, pady=2)

        self.engine_label = ctk.CTkLabel(
            stats_frame, text="No translations yet"
        )
        self.engine_label.pack(anchor="w", padx=5, pady=2)

        # Clear history button
        clear_btn = ctk.CTkButton(
            stats_frame,
            text="Clear History",
            command=self._on_clear_history,
            fg_color=("#C42B2B", "#8B1F1F"),
            hover_color=("#A32424", "#701919"),
        )
        clear_btn.pack(anchor="e", padx=5, pady=5)

    def _on_clear_history(self) -> None:
        """Handle clear history button click with confirmation"""
        try:
            result = CTkMessagebox(
                title="Clear History",
                message="Are you sure you want to clear all history?",
                icon="warning",
                option_1="Yes",
                option_2="No",
            ).get()

            if result == "Yes":
                self.controller.clear_history()
                self.show_toast("History cleared successfully")

        except Exception as e:
            logging.error(f"Error clearing history: {e}")
            self.show_error("Error", "Failed to clear history")

    def _on_close(self):
        """Handle window close"""
        self.destroy()

    def show_error(self, title: str, message: str):
        """Show error dialog"""
        CTkMessagebox(master=self, title=title, message=message, icon="cancel")

    def show_toast(self, message: str):
        """Show a temporary notification message"""
        self.toast_label.configure(text=message)
        self.after(2000, lambda: self.toast_label.configure(text=""))

    def _create_filter_panel(self):
        """Create filter panel"""
        filter_frame = ctk.CTkFrame(self.container)
        filter_frame.pack(fill="x", padx=5, pady=5)

        # Search entry
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)

        search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search...",
            textvariable=self.search_var,
            width=200,
        )
        search_entry.pack(side="left", padx=5)

        # Engine filter
        self.engine_var = ctk.StringVar(value=DEFAULT_ENGINE)
        self.engine_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.engine_var,
            values=[DEFAULT_ENGINE],
            command=self._on_engine_filter_change,
            width=150,
        )
        self.engine_menu.pack(side="left", padx=5)

        # Date filter
        self.date_var = ctk.StringVar(value=DATE_FILTER_OPTIONS[0])
        date_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.date_var,
            values=DATE_FILTER_OPTIONS,
            command=self._on_date_filter_change,
            width=150,
        )
        date_menu.pack(side="left", padx=5)

    def _create_list_and_detail_view(self):
        """Create split view with list and detail panels"""
        # Create horizontal split container
        split_container = ctk.CTkFrame(self.container)
        split_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Left side: History list
        list_frame = ctk.CTkFrame(split_container)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Scrollable frame for entries
        self.history_frame = ctk.CTkScrollableFrame(list_frame)
        self.history_frame.pack(fill="both", expand=True)

        # Right side: Detail view
        detail_frame = ctk.CTkFrame(split_container)
        detail_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # Source text
        source_frame = ctk.CTkFrame(detail_frame)
        source_frame.pack(fill="x", padx=5, pady=5)

        source_header = ctk.CTkFrame(source_frame)
        source_header.pack(fill="x")

        ctk.CTkLabel(source_header, text="Source Text").pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            source_header,
            text="Copy",
            width=60,
            command=lambda: self._copy_text(
                self.source_text.get("1.0", "end-1c")
            ),
        ).pack(side="right", padx=5)

        self.source_text: ctk.CTkTextbox = ctk.CTkTextbox(
            source_frame, height=100
        )
        self.source_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Translation text
        translation_frame = ctk.CTkFrame(detail_frame)
        translation_frame.pack(fill="both", expand=True, padx=5, pady=5)

        translation_header = ctk.CTkFrame(translation_frame)
        translation_header.pack(fill="x")

        ctk.CTkLabel(translation_header, text="Translation").pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            translation_header,
            text="Copy",
            width=60,
            command=lambda: self._copy_text(
                self.translation_text.get("1.0", "end-1c")
            ),
        ).pack(side="right", padx=5)

        self.translation_text: ctk.CTkTextbox = ctk.CTkTextbox(
            translation_frame
        )
        self.translation_text.pack(fill="both", expand=True, padx=5, pady=5)

    def _copy_text(self, text: str):
        """Copy text to clipboard"""
        pyperclip.copy(text)
        self.show_toast("Text copied to clipboard")
        self.controller.on_copy_text(text)

    def _update_engine_options(self):
        """Update engine filter options"""
        engines = set(entry.translation_engine for entry in self.entries)
        self.engine_var.set("All Engines")
        self.engine_menu.configure(
            values=["All Engines"] + sorted(list(engines))
        )

    def _apply_filters(self) -> None:
        """Apply filters efficiently using generator expressions"""
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None

        filtered = list(self.entries)

        # Apply engine filter
        engine = self.engine_var.get()
        if engine != DEFAULT_ENGINE:
            filtered = list(
                entry
                for entry in filtered
                if entry.translation_engine == engine
            )

        # Apply date filter
        date_filter = self._get_date_filter_function(self.date_var.get())
        filtered = list(filter(date_filter, filtered))

        # Apply search filter
        search_text = self.search_var.get().lower()
        if search_text:
            filtered = list(
                entry
                for entry in filtered
                if search_text in entry.source_text.lower()
                or search_text in entry.translated_text.lower()
            )

        # Convert to list for UI update
        self._update_filtered_entries(filtered)

    @staticmethod
    def _get_date_filter_function(
        filter_type: str,
    ) -> Callable[[TranslationEntry], bool]:
        """Get the appropriate date filter function based on filter type"""
        now = datetime.now()

        if filter_type == "All Time":
            return lambda entry: True
        elif filter_type == "Today":
            return lambda entry: entry.timestamp.date() == now.date()
        elif filter_type == "Last 7 Days":
            return lambda entry: (now - entry.timestamp).days <= 7
        elif filter_type == "Last 30 Days":
            return lambda entry: (now - entry.timestamp).days <= 30
        else:
            return lambda entry: True

    def _update_filtered_entries(
        self, filtered_entries: List[TranslationEntry]
    ) -> None:
        """Update UI with filtered entries"""
        self.filtered_entries = filtered_entries
        self._load_entries_chunk(0, CHUNK_SIZE)
        self._calculate_stats()

    def _on_search_change(self, *_):
        """Handle search text change with debouncing"""
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(DEBOUNCE_DELAY, self._apply_filters)

    def _on_engine_filter_change(self, _: str):
        """Handle engine filter change"""
        self._apply_filters()

    def _on_date_filter_change(self, _: str):
        """Handle date filter change"""
        self._apply_filters()

    def update_entries(self, entries: List[TranslationEntry]):
        """Update history entries"""
        self.entries = entries
        self.filtered_entries = entries.copy()
        self._calculate_stats()
        self._load_entries_chunk(0, CHUNK_SIZE)
        self._update_engine_options()

    @staticmethod
    def _create_entry_widgets(
        frame: ctk.CTkFrame, entry: TranslationEntry
    ) -> dict:
        """Create and layout widgets for an entry"""
        try:
            # Timestamp
            time_label = ctk.CTkLabel(
                frame,
                text=entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                font=("Helvetica", 10),
            )
            time_label.grid(row=0, column=0, sticky="w", padx=5)

            # Preview text (truncated)
            preview = (
                entry.translated_text[:PREVIEW_LENGTH] + "..."
                if len(entry.translated_text) > PREVIEW_LENGTH
                else entry.translated_text
            )
            preview_label = ctk.CTkLabel(
                frame, text=preview, anchor="w", justify="left"
            )
            preview_label.grid(row=0, column=1, sticky="ew", padx=5)

            # Engine and language info
            info_text = f"{
                entry.source_lang} → {
                entry.target_lang} | {
                entry.translation_engine}"
            info_label = ctk.CTkLabel(
                frame, text=info_text, font=("Helvetica", 10)
            )
            info_label.grid(row=0, column=2, sticky="e", padx=5)

            return {
                "time_label": time_label,
                "preview_label": preview_label,
                "info_label": info_label,
            }

        except Exception as e:
            logging.error(f"Error creating entry widgets: {e}")
            raise

    def _create_entry_widget(self, entry: TranslationEntry) -> None:
        """Create optimized entry widget with error handling"""
        try:
            frame = ctk.CTkFrame(self.history_frame)
            frame.pack(fill="x", padx=5, pady=2)

            # Use grid layout for better performance
            frame.grid_columnconfigure(1, weight=1)

            # Create widgets with error handling
            widgets = self._create_entry_widgets(frame, entry)
            self._setup_entry_bindings(frame, widgets, entry)

        except Exception as e:
            logging.error(f"Error creating entry widget: {e}")
            self.show_error("Error", "Failed to create history entry")

    def _setup_entry_bindings(
        self,
        frame: ctk.CTkFrame,
        widgets: dict,
        current_entry: TranslationEntry,
    ) -> None:
        """Setup event bindings for entry widgets"""
        try:

            def on_click(_event, entry=current_entry):
                self._show_entry_details(entry)

            def on_enter(_event):
                frame.configure(fg_color=("gray75", "gray30"))

            def on_leave(_event):
                frame.configure(fg_color=("gray85", "gray25"))

            # Configure frame
            frame.configure(fg_color=("gray85", "gray25"), cursor="hand2")

            # Bind events to frame and all labels
            for widget in [frame] + list(widgets.values()):
                widget.bind("<Button-1>", on_click)
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)

                # Make labels look clickable
                if isinstance(widget, ctk.CTkLabel):
                    widget.configure(cursor="hand2")

        except Exception as e:
            logging.error(f"Error setting up entry bindings: {e}")
            raise

    def _show_entry_details(self, entry: TranslationEntry) -> None:
        """Show entry details efficiently"""

        def update_text() -> None:
            for widget, text in [
                (self.source_text, entry.source_text),
                (self.translation_text, entry.translated_text),
            ]:
                widget.configure(state="normal")
                widget.delete("1.0", "end")
                widget.insert("1.0", text)
                widget.configure(state="disabled")

        self.after(10, update_text)
