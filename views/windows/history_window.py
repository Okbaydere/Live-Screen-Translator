import customtkinter as ctk
from typing import Protocol, List, Optional
import logging
from datetime import datetime
import pyperclip
from models.translation_model import TranslationEntry

try:
    from CTkMessagebox import CTkMessagebox
except ImportError:
    # Fallback to basic dialog if CTkMessagebox is not installed
    class CTkMessagebox:
        def __init__(self, **kwargs):
            title = kwargs.get('title', 'Message')
            message = kwargs.get('message', '')
            icon = kwargs.get('icon', 'info')
            
            dialog = ctk.CTkInputDialog(
                text=message,
                title=title
            )
            dialog.geometry("400x200")  # Make dialog bigger
            
            # Hide the input field since we only want to show a message
            for child in dialog.winfo_children():
                if isinstance(child, ctk.CTkEntry):
                    child.pack_forget()
                    
            # Add an OK button
            ctk.CTkButton(
                dialog,
                text="OK",
                command=dialog.destroy
            ).pack(pady=10)

class HistoryWindowProtocol(Protocol):
    """Protocol defining the interface for history window callbacks"""
    def on_close(self): ...
    def on_clear_history(self): ...
    def on_copy_text(self, text: str): ...
    def on_filter_change(self, filter_type: str, value: str): ...

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, controller: HistoryWindowProtocol):
        super().__init__(parent)
        
        self.controller = controller
        self.entries = []
        self.filtered_entries = []
        self._search_after_id = None  # For search debouncing
        
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
        self.update_stats({
            'total_entries': 0,
            'unique_sources': 0,
            'unique_targets': 0,
            'engines_used': [],
            'most_used_engine': None,
            'engine_usage': {}
        })
        
    def load_entries(self, entries: List[TranslationEntry]):
        """Load history entries"""
        self.entries = entries
        self.filtered_entries = entries.copy()
        
        # Pre-calculate stats
        self._calculate_stats()
        
        # Load entries in chunks
        self.after(10, self._load_entries_chunk, 0, 20)
        
    def _calculate_stats(self):
        """Pre-calculate statistics"""
        if not self.entries:
            self._stats = {
                'total_entries': 0,
                'unique_sources': 0,
                'unique_targets': 0,
                'engines_used': [],
                'most_used_engine': None,
                'engine_usage': {}
            }
            return
            
        engines_count = {}
        sources = set()
        targets = set()
        
        for entry in self.entries:
            engines_count[entry.translation_engine] = engines_count.get(entry.translation_engine, 0) + 1
            sources.add(entry.source_lang)
            targets.add(entry.target_lang)
            
        most_used_engine = max(engines_count.items(), key=lambda x: x[1])[0] if engines_count else None
        
        self._stats = {
            'total_entries': len(self.entries),
            'unique_sources': len(sources),
            'unique_targets': len(targets),
            'engines_used': list(engines_count.keys()),
            'most_used_engine': most_used_engine,
            'engine_usage': engines_count
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
        self.total_label.configure(text=f"Total Entries: {stats['total_entries']}")
        self.sources_label.configure(text=f"Unique Source Languages: {stats['unique_sources']}")
        self.targets_label.configure(text=f"Unique Target Languages: {stats['unique_targets']}")
        
        if stats['most_used_engine']:
            engine_text = f"Most Used Engine: {stats['most_used_engine']}"
            if stats['engine_usage']:
                usage = stats['engine_usage'][stats['most_used_engine']]
                engine_text += f" ({usage} times)"
            self.engine_label.configure(text=engine_text)
        else:
            self.engine_label.configure(text="No translations yet")
            
    def _create_stats_panel(self):
        """Create statistics panel"""
        stats_frame = ctk.CTkFrame(self.container)
        stats_frame.pack(fill="x", padx=5, pady=5)
        
        # Toast label for notifications
        self.toast_label = ctk.CTkLabel(stats_frame, text="", text_color="gray")
        self.toast_label.pack(anchor="w", padx=5, pady=2)
        
        self.total_label = ctk.CTkLabel(stats_frame, text="Total Entries: 0")
        self.total_label.pack(anchor="w", padx=5, pady=2)
        
        self.sources_label = ctk.CTkLabel(stats_frame, text="Unique Source Languages: 0")
        self.sources_label.pack(anchor="w", padx=5, pady=2)
        
        self.targets_label = ctk.CTkLabel(stats_frame, text="Unique Target Languages: 0")
        self.targets_label.pack(anchor="w", padx=5, pady=2)
        
        self.engine_label = ctk.CTkLabel(stats_frame, text="No translations yet")
        self.engine_label.pack(anchor="w", padx=5, pady=2)
        
        # Clear history button
        clear_btn = ctk.CTkButton(
            stats_frame,
            text="Clear History",
            command=self._on_clear_history,
            fg_color=("#C42B2B", "#8B1F1F"),
            hover_color=("#A32424", "#701919")
        )
        clear_btn.pack(anchor="e", padx=5, pady=5)
        
    def _on_clear_history(self):
        """Handle clear history button click"""
        try:
            self.controller.clear_history()
        except Exception as e:
            logging.error(f"Error clearing history: {e}")
            self.show_error("Error", "Failed to clear history")
            
    def _on_close(self):
        """Handle window close"""
        self.destroy()
        
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        CTkMessagebox(
            master=self,
            title=title,
            message=message,
            icon="cancel"
        )
        
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
            width=200
        )
        search_entry.pack(side="left", padx=5)
        
        # Engine filter
        self.engine_var = ctk.StringVar(value="All Engines")
        self.engine_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.engine_var,
            values=["All Engines"],
            command=self._on_engine_filter_change,
            width=150
        )
        self.engine_menu.pack(side="left", padx=5)
        
        # Date filter
        self.date_var = ctk.StringVar(value="All Time")
        date_menu = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.date_var,
            values=["All Time", "Today", "Last 7 Days", "Last 30 Days"],
            command=self._on_date_filter_change,
            width=150
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
        
        ctk.CTkLabel(source_header, text="Source Text").pack(side="left", padx=5)
        ctk.CTkButton(
            source_header,
            text="Copy",
            width=60,
            command=lambda: self._copy_text(self.source_text.get("1.0", "end-1c"))
        ).pack(side="right", padx=5)
        
        self.source_text = ctk.CTkTextbox(source_frame, height=100)
        self.source_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Translation text
        translation_frame = ctk.CTkFrame(detail_frame)
        translation_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        translation_header = ctk.CTkFrame(translation_frame)
        translation_header.pack(fill="x")
        
        ctk.CTkLabel(translation_header, text="Translation").pack(side="left", padx=5)
        ctk.CTkButton(
            translation_header,
            text="Copy",
            width=60,
            command=lambda: self._copy_text(self.translation_text.get("1.0", "end-1c"))
        ).pack(side="right", padx=5)
        
        self.translation_text = ctk.CTkTextbox(translation_frame)
        self.translation_text.pack(fill="both", expand=True, padx=5, pady=5)
        
    def _copy_text(self, text: str):
        """Copy text to clipboard"""
        pyperclip.copy(text)
        self.show_toast("Text copied to clipboard")
        self.controller.on_copy_text(text)
        
    def _show_stats(self):
        """Show translation statistics"""
        if not self.entries:
            CTkMessagebox(
                title="Statistics",
                message="No translations in history.",
                icon="info"
            )
            return
            
        # Calculate statistics
        total_translations = len(self.entries)
        
        # Count unique engines and languages
        translation_engines = set(entry.translation_engine for entry in self.entries)
        source_languages = set(entry.source_lang for entry in self.entries)
        target_languages = set(entry.target_lang for entry in self.entries)
        
        # Get time range
        if self.entries:
            first_translation = min(entry.timestamp for entry in self.entries)
            last_translation = max(entry.timestamp for entry in self.entries)
            time_range = last_translation - first_translation
            days = time_range.days
            hours = time_range.seconds // 3600
            minutes = (time_range.seconds % 3600) // 60
            
            time_str = ""
            if days > 0:
                time_str += f"{days} days "
            if hours > 0:
                time_str += f"{hours} hours "
            if minutes > 0:
                time_str += f"{minutes} minutes"
            if not time_str:
                time_str = "less than a minute"
        
        # Format message
        stats_message = f"Total Translations: {total_translations}\n\n"
        stats_message += f"Translation Engines Used: {', '.join(translation_engines)}\n"
        stats_message += f"Source Languages: {', '.join(source_languages)}\n"
        stats_message += f"Target Languages: {', '.join(target_languages)}\n\n"
        stats_message += f"Time Range: {time_str}"
        
        CTkMessagebox(
            title="Translation Statistics",
            message=stats_message,
            icon="info"
        )
        
    def _update_engine_options(self):
        """Update engine filter options"""
        engines = set(entry.translation_engine for entry in self.entries)
        self.engine_var.set("All Engines")
        self.engine_menu.configure(values=["All Engines"] + sorted(list(engines)))
        
    def _apply_filters(self):
        """Apply filters efficiently"""
        # Cancel any pending search
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None
            
        # Get filter values
        search_text = self.search_var.get().lower()
        engine = self.engine_var.get()
        date_filter = self.date_var.get()
        
        # Start with all entries
        filtered = self.entries
        
        # Apply engine filter first (usually most restrictive)
        if engine != "All Engines":
            filtered = [entry for entry in filtered if entry.translation_engine == engine]
            
        # Apply date filter
        if date_filter != "All Time":
            now = datetime.now()
            if date_filter == "Today":
                filtered = [entry for entry in filtered if entry.timestamp.date() == now.date()]
            elif date_filter == "Last 7 Days":
                filtered = [entry for entry in filtered if (now - entry.timestamp).days <= 7]
            elif date_filter == "Last 30 Days":
                filtered = [entry for entry in filtered if (now - entry.timestamp).days <= 30]
                
        # Apply search filter last
        if search_text:
            filtered = [
                entry for entry in filtered
                if search_text in entry.source_text.lower() or 
                   search_text in entry.translated_text.lower()
            ]
            
        self.filtered_entries = filtered
        self.after(10, self._load_entries_chunk, 0, 20)
        
    def _on_search_change(self, *args):
        """Handle search text change with debouncing"""
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self._apply_filters)
        
    def _on_engine_filter_change(self, value: str):
        """Handle engine filter change"""
        self._apply_filters()
        
    def _on_date_filter_change(self, value: str):
        """Handle date filter change"""
        self._apply_filters()
        
    def update_entries(self, entries: List[TranslationEntry]):
        """Update history entries"""
        self.entries = entries
        self._apply_filters() 
        
    def _create_entry_widget(self, entry: TranslationEntry):
        """Create optimized entry widget"""
        frame = ctk.CTkFrame(self.history_frame)
        frame.pack(fill="x", padx=5, pady=2)
        
        # Use single frame with grid layout for better performance
        frame.grid_columnconfigure(1, weight=1)
        
        # Timestamp
        time_label = ctk.CTkLabel(
            frame,
            text=entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            font=("Helvetica", 10)
        )
        time_label.grid(row=0, column=0, sticky="w", padx=5)
        
        # Preview text (truncated)
        preview = entry.translated_text[:50] + "..." if len(entry.translated_text) > 50 else entry.translated_text
        preview_label = ctk.CTkLabel(
            frame,
            text=preview,
            anchor="w",
            justify="left"
        )
        preview_label.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Engine and language info
        info_text = f"{entry.source_lang} → {entry.target_lang} | {entry.translation_engine}"
        info_label = ctk.CTkLabel(
            frame,
            text=info_text,
            font=("Helvetica", 10)
        )
        info_label.grid(row=0, column=2, sticky="e", padx=5)
        
        # Make everything clickable and add hover effects
        def on_click(e, entry=entry):
            self._show_entry_details(entry)
            
        def on_enter(e):
            frame.configure(fg_color=("gray75", "gray30"))
            
        def on_leave(e):
            frame.configure(fg_color=("gray85", "gray25"))
            
        # Configure frame
        frame.configure(fg_color=("gray85", "gray25"))
        
        # Bind events to frame and all labels
        for widget in [frame, time_label, preview_label, info_label]:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            
            # Make labels look clickable
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(cursor="hand2")  # Change cursor to hand when hovering
                
        # Make the frame look clickable too
        frame.configure(cursor="hand2")
        
    def _show_entry_details(self, entry: TranslationEntry):
        """Show entry details efficiently"""
        def update_text():
            # Update source text
            self.source_text.configure(state="normal")
            self.source_text.delete("1.0", "end")
            self.source_text.insert("1.0", entry.source_text)
            
            # Update translation text
            self.translation_text.configure(state="normal")
            self.translation_text.delete("1.0", "end")
            self.translation_text.insert("1.0", entry.translated_text)
            
        # Schedule text update to prevent UI freezing
        self.after(10, update_text) 