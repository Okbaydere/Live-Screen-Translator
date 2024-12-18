import logging
import customtkinter as ctk
from typing import List, Optional, Protocol
from datetime import datetime
from models.translation_model import TranslationModel, TranslationEntry
from views.windows.history_window import HistoryWindow

class HistoryWindowProtocol(Protocol):
    def show_history_window(self): ...
    def get_history_by_languages(self, source_lang: str, target_lang: str) -> List[TranslationEntry]: ...
    def search_history(self, query: str) -> List[TranslationEntry]: ...
    def get_history_stats(self) -> dict: ...
    def clear_history(self): ...

class HistoryController(HistoryWindowProtocol):
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
                
                # Update statistics
                stats = self.get_history_stats()
                self.history_window.update_stats(stats)
            else:
                self.history_window.focus()
                
        except Exception as e:
            logging.error(f"Error showing history window: {e}")
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
            if query in entry.source_text.lower() or query in entry.translated_text.lower()
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
            
        most_used_engine = max(engines_count.items(), key=lambda x: x[1])[0]
        
        return {
            'total_entries': len(history),
            'unique_sources': len(sources),
            'unique_targets': len(targets),
            'engines_used': list(engines_count.keys()),
            'most_used_engine': most_used_engine,
            'engine_usage': engines_count
        }
        
    def clear_history(self):
        """Clear translation history"""
        try:
            self.translation_model.clear_history()
            if self.history_window and self.history_window.winfo_exists():
                self.history_window.load_entries([])
                self.history_window.update_stats(self.get_history_stats())
        except Exception as e:
            logging.error(f"Error clearing history: {e}")
            raise
            
    def cleanup(self):
        """Clean up resources"""
        if self.history_window:
            self.history_window.destroy()
            self.history_window = None