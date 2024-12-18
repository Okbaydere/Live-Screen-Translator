import logging
import customtkinter as ctk
from typing import List, Optional
from models.translation_model import TranslationModel, TranslationEntry
from views.windows.history_window import HistoryWindow

class HistoryController:
    def __init__(self, root: ctk.CTk, translation_model: TranslationModel):
        self.root = root
        self.translation_model = translation_model
        self.history_window: Optional[HistoryWindow] = None
        
    def show_history_window(self):
        """Show history window"""
        try:
            if self.history_window is None or not self.history_window.winfo_exists():
                self.history_window = HistoryWindow(self.root, self)
                self.history_window.title("Translation History")
                self.history_window.geometry("800x600")
                self.history_window.minsize(600, 400)
                
                # Load history entries
                entries = self.translation_model.get_history()
                self.history_window.load_entries(entries)
            else:
                self.history_window.focus()
                
        except Exception as exc:
            logging.error(f"Error showing history window: {exc}")
            raise
            
    def get_history_by_languages(self, source_lang: str, target_lang: str) -> List[TranslationEntry]:
        """Get history entries for specific language pair"""
        return [
            entry for entry in self.translation_model.get_history()
            if entry.source_lang == source_lang and entry.target_lang == target_lang
        ]
        
    def search_history(self, query: str) -> List[TranslationEntry]:
        """Search history entries"""
        query = query.lower()
        return [
            entry for entry in self.translation_model.get_history()
            if query in entry.source_text.lower() or 
               query in entry.translated_text.lower()
        ]
        
    def get_history_stats(self) -> dict:
        """Get history statistics"""
        history = self.translation_model.get_history()
        if not history:
            return {
                'total_entries': 0,
                'unique_sources': 0,
                'unique_targets': 0,
                'engines_used': [],
                'most_used_engine': None,
                'engine_usage': {}
            }
            
        engines_count = {}
        sources = set()
        targets = set()
        
        for entry in history:
            engines_count[entry.translation_engine] = engines_count.get(entry.translation_engine, 0) + 1
            sources.add(entry.source_lang)
            targets.add(entry.target_lang)
            
        most_used_engine = max(engines_count.items(), key=lambda x: x[1])[0] if engines_count else None
        
        return {
            'total_entries': len(history),
            'unique_sources': len(sources),
            'unique_targets': len(targets),
            'engines_used': list(engines_count.keys()),
            'most_used_engine': most_used_engine,
            'engine_usage': engines_count
        }
        
    def clear_history(self) -> None:
        """Clear translation history"""
        try:
            self.translation_model.clear_history()
        except Exception as err:
            logging.error(f"Error clearing history: {err}")
            raise
            
    def on_close(self) -> None:
        """Handle window close"""
        self.history_window = None
        
    def on_copy_text(self, text: str) -> None:
        """Handle text copy"""
        pass  # No specific action needed
        
    def on_filter_change(self, filter_type: str, value: str) -> None:
        """Handle filter change"""
        pass  # No specific action needed
        
    def cleanup(self):
        """Clean up resources"""
        if self.history_window:
            self.history_window.destroy()
            self.history_window = None