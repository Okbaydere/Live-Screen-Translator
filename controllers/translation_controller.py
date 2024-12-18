import logging
import threading
import time
import traceback
import asyncio
from datetime import datetime
from typing import Optional, Tuple
from PIL import Image, ImageGrab
import customtkinter as ctk

from models.translation_model import TranslationModel, TranslationEntry
from models.config_model import ConfigModel
from models.ocr_model import OCRModel
from models.region_model import RegionModel
from views.windows.translation_window import TranslationWindow, TranslationWindowProtocol

class TranslationController(TranslationWindowProtocol):
    def __init__(self, root: ctk.CTk, translation_model: TranslationModel, 
                 config_model: ConfigModel, ocr_model: OCRModel, window_controller):
        self.root = root
        self.translation_model = translation_model
        self.config_model = config_model
        self.ocr_model = ocr_model
        self.region_model = RegionModel()
        self.window_controller = window_controller
        
        # State
        self.selected_region = None
        self.is_translating = False
        self.translation_thread = None
        self._last_ocr_text = ""
        self.translation_window = None
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        
    def select_screen_region(self) -> bool:
        """Select screen region for translation"""
        try:
            logging.info("Attempting to select screen region")
            self.root.withdraw()
            
            selected_region = self.region_model.select_region()
            
            self.root.deiconify()
            
            if selected_region:
                logging.info(f"Region selected: {selected_region}")
                self.selected_region = selected_region
                return True
            else:
                logging.warning("No region was selected")
                self.selected_region = None
                return False
                
        except Exception as exc:
            logging.error(f"Error in region selection: {exc}")
            logging.error(traceback.format_exc())
            return False
        finally:
            self.root.deiconify()
            
    def start_translation(self):
        """Start translation process"""
        if not self.selected_region:
            raise ValueError("No region selected")
            
        self.is_translating = True
        self._last_ocr_text = ""
        
        # Create translation window if needed
        if not self.translation_window:
            self._create_translation_window()
            
        # Start translation thread
        self.translation_thread = threading.Thread(
            target=self._run_async_worker,
            daemon=True
        )
        self.translation_thread.start()
        
        # Notify main controller that translation has started
        self.root.event_generate("<<TranslationStarted>>")
        
    def stop_translation(self):
        """Stop translation process"""
        if self.is_translating:
            logging.info("Stopping translation...")
            self.is_translating = False
            
            if self.translation_thread and self.translation_thread.is_alive():
                self.translation_thread.join(timeout=0.1)
                
        if self.translation_window:
            try:
                self.translation_window.destroy()
            except Exception as e:
                logging.error(f"Error destroying translation window: {e}")
            finally:
                self.translation_window = None
                
        # Notify main controller that translation has stopped
        self.root.event_generate("<<TranslationStopped>>")
            
    def _create_translation_window(self):
        """Create translation window"""
        opacity = self.config_model.get_config('window', 'opacity', 90) / 100
        is_game_mode = self.config_model.get_config('window', 'game_mode', False)
        
        self.translation_window = TranslationWindow(
            parent=self.root,
            controller=self,
            window_controller=self.window_controller,
            opacity=opacity,
            initial_text=""
        )
        
        # Set initial opacity before game mode
        self.translation_window.attributes('-alpha', opacity)
        
        # Set initial game mode
        if is_game_mode:
            self.translation_window.set_game_mode(True)
            
        # Ensure window is visible and on top
        self.translation_window.lift()
        self.translation_window.focus_force()
        self.translation_window.attributes('-topmost', True)  # Force topmost
        
        # Position window in the center of the screen
        window_width = 400
        window_height = 200
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.translation_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
    def _run_async_worker(self):
        """Run the async translation worker in the thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._translation_worker())
        finally:
            loop.close()
            
    async def _translation_worker(self):
        """Worker function for translation"""
        try:
            while self.is_translating:
                # Get screenshot of selected region
                screenshot = await self._capture_region()
                if screenshot is None:
                    continue
                    
                # Process image with OCR
                source_lang = self.config_model.get_config('translation', 'source_lang', 'auto')
                ocr_text = await self.ocr_model.process_image(screenshot, source_lang)
                
                if not ocr_text:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Only translate if text has changed
                if ocr_text == self._last_ocr_text:
                    await asyncio.sleep(0.1)
                    continue
                    
                self._last_ocr_text = ocr_text
                
                # Get target language from config
                target_lang = self.config_model.get_config('translation', 'target_lang', 'en')
                
                # Translate text
                translated_text = await self._translate_text(ocr_text, source_lang, target_lang)
                
                if not translated_text:
                    continue
                    
                # Update translation window
                if self.translation_window:
                    self.root.after(0, lambda t=translated_text: self.translation_window.set_text(t))
                    
                # Add to history
                entry = TranslationEntry(
                    source_text=ocr_text,
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    translation_engine=self.translation_model.get_current_engine(),
                    timestamp=datetime.now()
                )
                self.translation_model.add_to_history(
                    source_text=ocr_text,
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                
                # Small delay to prevent high CPU usage
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logging.info("Translation worker cancelled")
            raise
        except Exception as e:
            logging.error(f"Translation error: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            self.root.event_generate("<<TranslationError>>")
            raise
            
    async def _capture_region(self):
        """Capture screenshot of selected region"""
        try:
            return ImageGrab.grab(bbox=self.selected_region)
        except Exception as e:
            logging.error(f"Error capturing region: {e}")
            return None
            
    async def _translate_text(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Translate text using the translation model"""
        try:
            return await self.translation_model.translate(
                text,
                source_lang=source_lang,
                target_lang=target_lang
            )
        except Exception as e:
            logging.error(f"Translation error: {e}")
            return None
            
    # TranslationWindowProtocol implementation
    def on_close(self):
        """Handle translation window closing"""
        self.stop_translation()  # This will trigger the TranslationStopped event
        
    def on_copy_text(self, text: str):
        """Handle text copy"""
        logging.info("Text copied to clipboard")
        
    def on_window_move(self, x: int, y: int):
        """Handle window movement"""
        # Save window position to config if needed
        pass
        
    # Engine management
    def change_translation_engine(self, engine: str):
        """Change translation engine"""
        try:
            self.translation_model.set_translation_engine(engine)
            self.config_model.update_config('translation', 'engine', engine)
            
        except Exception as e:
            logging.error(f"Error changing translation engine: {e}")
            raise
            
    def change_ocr_engine(self, engine: str):
        """Change OCR engine"""
        try:
            self.ocr_model.set_engine(engine)
            self.config_model.update_config('ocr', 'engine', engine)
            
        except Exception as e:
            logging.error(f"Error changing OCR engine: {e}")
            raise
            
    def cycle_translation_engine(self) -> str:
        """Cycle to next translation engine"""
        engines = self.translation_model.get_available_engines()
        current = self.translation_model.get_current_engine()
        next_index = (engines.index(current) + 1) % len(engines)
        next_engine = engines[next_index]
        
        self.change_translation_engine(next_engine)
        return next_engine
        
    def cycle_ocr_engine(self) -> str:
        """Cycle to next OCR engine"""
        return self.ocr_model.cycle_engine()
        
    def get_translation_history(self):
        """Get translation history"""
        return self.translation_model.get_history()
        
    def clear_translation_history(self):
        """Clear translation history"""
        self.translation_model.clear_history() 
        
    def _update_translation_window(self, text: str):
        """Update translation window text and ensure visibility"""
        if self.translation_window:
            self.translation_window.set_text(text)
            self.translation_window.lift()  # Ensure window stays on top
            self.translation_window.focus_force()  # Force focus to keep window visible
        
    def cleanup(self):
        """Clean up resources before exit"""
        try:
            self.stop_translation()
            if self.translation_model:
                self.translation_model.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")