import tkinter as tk
import customtkinter as ctk
from datetime import datetime

class TranslationHistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent, translation_history, ui_manager):
        super().__init__(parent)
        
        self.translation_history = translation_history
        self.ui_manager = ui_manager
        
        # Window configuration
        self.title("Translation History")
        self.geometry("800x600")
        self.attributes('-topmost', True)
        
        # Create main container
        self.create_ui()
        
    def create_ui(self):
        """Create the history window UI"""
        # Create scrollable frame
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create headers
        self.create_headers()
        
        # Load initial entries
        self.load_history_chunk(0, 20)
        
        # Clear history button
        clear_btn = ctk.CTkButton(
            self,
            text="Clear History",
            command=self.clear_history
        )
        clear_btn.pack(pady=10)
        
    def create_headers(self):
        """Create header row"""
        headers = ["Time", "Source Text", "Translation", "OCR", "Translation Engine", "Languages"]
        for col, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.scroll_frame,
                text=header,
                font=("Helvetica", 12, "bold")
            )
            label.grid(row=0, column=col, padx=5, pady=5, sticky="w")
            
    def load_history_chunk(self, start_idx, chunk_size):
        """Load a chunk of history entries"""
        history = self.translation_history.get_history()
        end_idx = min(start_idx + chunk_size, len(history))
        
        for row, entry in enumerate(history[start_idx:end_idx], start=start_idx + 1):
            # Time
            time_label = ctk.CTkLabel(
                self.scroll_frame,
                text=datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S"),
                wraplength=100
            )
            time_label.grid(row=row, column=0, padx=5, pady=5, sticky="nw")
            
            # Source text
            source_text = entry['source_text']
            truncated_source = source_text[:500] + ('...' if len(source_text) > 500 else '')
            source_label = ctk.CTkLabel(
                self.scroll_frame,
                text=truncated_source,
                wraplength=150,
                cursor="hand2" if len(source_text) > 500 else ""
            )
            source_label.grid(row=row, column=1, padx=5, pady=5, sticky="nw")
            if len(source_text) > 500:
                source_label.bind("<Button-1>", lambda e, text=source_text: self.show_full_text("Source Text", text))
                
            # Translation
            translated_text = entry['translated_text']
            truncated_trans = translated_text[:500] + ('...' if len(translated_text) > 500 else '')
            trans_label = ctk.CTkLabel(
                self.scroll_frame,
                text=truncated_trans,
                wraplength=150,
                cursor="hand2" if len(translated_text) > 500 else ""
            )
            trans_label.grid(row=row, column=2, padx=5, pady=5, sticky="nw")
            if len(translated_text) > 500:
                trans_label.bind("<Button-1>", lambda e, text=translated_text: self.show_full_text("Translation", text))
                
            # OCR Engine
            ocr_label = ctk.CTkLabel(
                self.scroll_frame,
                text=entry['ocr_engine']
            )
            ocr_label.grid(row=row, column=3, padx=5, pady=5, sticky="nw")
            
            # Translation Engine
            engine_label = ctk.CTkLabel(
                self.scroll_frame,
                text=entry['translation_engine']
            )
            engine_label.grid(row=row, column=4, padx=5, pady=5, sticky="nw")
            
            # Languages
            lang_label = ctk.CTkLabel(
                self.scroll_frame,
                text=f"{entry['source_lang']} → {entry['target_lang']}"
            )
            lang_label.grid(row=row, column=5, padx=5, pady=5, sticky="nw")
            
        # Load more button if there are more entries
        if end_idx < len(history):
            load_more_btn = ctk.CTkButton(
                self.scroll_frame,
                text="Load More",
                command=lambda: self.load_more_history(end_idx)
            )
            load_more_btn.grid(row=end_idx + 1, column=0, columnspan=6, pady=10)
            
    def load_more_history(self, start_idx):
        """Load more history entries"""
        # Remove existing load more button
        for widget in self.scroll_frame.grid_slaves():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "Load More":
                widget.destroy()
        # Load next chunk
        self.load_history_chunk(start_idx, 20)
        
    def show_full_text(self, title, text):
        """Show full text in a dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("600x400")
        dialog.attributes('-topmost', True)
        
        # Create text widget
        text_frame = ctk.CTkFrame(dialog)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = ctk.CTkTextbox(
            text_frame,
            wrap="word",
            font=("Helvetica", 12)
        )
        text_widget.pack(fill="both", expand=True)
        
        # Insert text
        text_widget.insert("1.0", text)
        text_widget.configure(state="disabled")
        
        # Copy button
        copy_btn = ctk.CTkButton(
            dialog,
            text="Copy to Clipboard",
            command=lambda: self.copy_to_clipboard(text)
        )
        copy_btn.pack(pady=10)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.ui_manager.show_toast("Text copied to clipboard")
        
    def clear_history(self):
        """Clear translation history"""
        if tk.messagebox.askyesno("Clear History", "Are you sure you want to clear the translation history?"):
            self.translation_history.clear_history()
            self.destroy() 