import asyncio
import logging
import threading
import traceback
from typing import Optional, Tuple

import customtkinter as ctk
from PIL import ImageGrab

from models.config_model import ConfigModel
from models.ocr_model import OCRModel
from models.region_model import RegionModel
from models.translation_model import TranslationModel
from views.windows.translation_window import (TranslationWindow,
                                              TranslationWindowProtocol)


class TranslationController(TranslationWindowProtocol):
    def __init__(
        self,
        root: ctk.CTk,
        translation_model: TranslationModel,
        config_model: ConfigModel,
        ocr_model: OCRModel,
        window_controller,
    ):
        self.root = root
        self.translation_model = translation_model
        self.config_model = config_model
        self.ocr_model = ocr_model
        self.region_model = RegionModel()
        self.window_controller = window_controller

        # State
        self.selected_region: Optional[Tuple[int, int, int, int]] = None
        self.is_translating = False
        self.translation_thread: Optional[threading.Thread] = None
        self._last_ocr_text = ""
        self.translation_window: Optional[TranslationWindow] = None

        # Initialize logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

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

        # Create and start translation thread
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
        try:
            opacity = self.config_model.get_config(
                "window", "opacity", 90) / 100
            logging.info(
                f"Creating translation window with opacity: {opacity}")

            self.translation_window = TranslationWindow(
                parent=self.root,
                controller=self,
                window_controller=self.window_controller,
                opacity=opacity,
                initial_text="",
            )

            if self.translation_window is not None:
                # Set window properties
                self.translation_window.attributes("-alpha", opacity)
                self.translation_window.lift()
                self.translation_window.focus_force()
                self.translation_window.attributes("-topmost", True)

                # Position window in the center of the screen
                window_width = 400
                window_height = 200
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
                self.translation_window.geometry(
                    f"{window_width}x{window_height}+{x}+{y}")

                logging.info("Translation window created successfully")
            else:
                logging.error("Failed to create translation window")

        except Exception as e:
            logging.error(f"Error creating translation window: {e}")
            raise

    def _run_async_worker(self):
        """Run the async translation worker in the thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._translation_worker())
        finally:
            loop.close()

    async def _check_translation_window(self) -> bool:
        """Check if translation window exists and is valid"""
        if not self.translation_window:
            logging.warning(
                "Translation window does not exist, stopping translation"
            )
            self.stop_translation()
            return False
        return True

    async def _process_and_translate(
        self, screenshot
    ) -> Optional[tuple[str, str]]:
        """Process image with OCR and translate the text"""
        source_lang = self.config_model.get_config(
            "translation", "source_lang", "auto"
        )
        logging.info("Starting OCR processing...")
        ocr_text = await self.ocr_model.process_image(screenshot, source_lang)
        logging.info(f"OCR Result: {ocr_text}")

        if not ocr_text or ocr_text == self._last_ocr_text:
            return None

        self._last_ocr_text = ocr_text
        target_lang = self.config_model.get_config(
            "translation", "target_lang", "en"
        )
        logging.info("Starting translation...")
        translated_text = await self._translate_text(
            ocr_text, source_lang, target_lang
        )
        logging.info(f"Translation Result: {translated_text}")

        if not translated_text:
            return None

        return ocr_text, translated_text

    async def _update_window_and_history(
        self, ocr_text: str, translated_text: str
    ):
        """Update translation window and add to history"""
        if (
            self.translation_window is None
            or not self.translation_window.winfo_exists()
        ):
            logging.warning(
                "Translation window was destroyed, stopping translation"
            )
            self.stop_translation()
            return False

        try:
            logging.info(
                f"Attempting to update window with text: {translated_text}")
            # Directly update the window instead of using after
            self._update_translation_window(translated_text)

            source_lang = self.config_model.get_config(
                "translation", "source_lang", "auto"
            )
            target_lang = self.config_model.get_config(
                "translation", "target_lang", "en"
            )

            self.translation_model.add_to_history(
                source_text=ocr_text,
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
            )
            return True
        except Exception as e:
            logging.error(f"Error updating window and history: {e}")
            return False

    async def _translation_worker(self):
        """Worker function for translation"""
        try:
            logging.info("Translation worker started")
            while self.is_translating:
                if not await self._check_translation_window():
                    logging.warning("Translation window check failed")
                    break

                screenshot = await self._capture_region()
                if screenshot is None:
                    logging.warning(
                        "Failed to capture screenshot, retrying...")
                    await asyncio.sleep(0.1)
                    continue

                result = await self._process_and_translate(screenshot)
                if result is None:
                    logging.debug("No new text to translate, waiting...")
                    await asyncio.sleep(0.1)
                    continue

                ocr_text, translated_text = result
                logging.info(
                    f"Processing complete - OCR: {ocr_text[:50]}... Translation: {translated_text[:50]}...")

                if not await self._update_window_and_history(
                    ocr_text, translated_text
                ):
                    logging.warning("Failed to update window and history")
                    break

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
            logging.info(
                f"Attempting to capture region: {
                    self.selected_region}")
            screenshot = ImageGrab.grab(bbox=self.selected_region)
            if screenshot:
                logging.info("Screenshot captured successfully")
                return screenshot
            else:
                logging.error("Failed to capture screenshot")
                return None
        except Exception as e:
            logging.error(f"Error capturing region: {e}")
            return None

    async def _translate_text(
        self, text: str, source_lang: str, target_lang: str
    ) -> Optional[str]:
        """Translate text using the translation model"""
        try:
            return await self.translation_model.translate(
                text, source_lang=source_lang, target_lang=target_lang
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
            self.config_model.update_config("translation", "engine", engine)

        except Exception as e:
            logging.error(f"Error changing translation engine: {e}")
            raise

    def change_ocr_engine(self, engine: str):
        """Change OCR engine"""
        try:
            self.ocr_model.set_engine(engine)
            self.config_model.update_config("ocr", "engine", engine)

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
        """Update translation window text safely"""
        try:
            if not self.translation_window:
                logging.error("Translation window is None")
                return False

            if not self.translation_window.winfo_exists():
                logging.error("Translation window does not exist")
                return False

            logging.info(f"Setting text in translation window: {text}")

            # Use after_idle to ensure update happens in the main thread
            self.root.after_idle(lambda: self._do_update_text(text))
            return True

        except Exception as e:
            logging.error(f"Error updating translation window: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False

    def _do_update_text(self, text: str):
        """Actually update the text in the main thread"""
        try:
            if self.translation_window and self.translation_window.winfo_exists():
                success = self.translation_window.set_text(text)
                if success:
                    logging.info("Successfully updated translation window")
                    self.translation_window.lift()
                    self.translation_window.focus_force()
                else:
                    logging.error("Failed to set text in translation window")
        except Exception as e:
            logging.error(f"Error in _do_update_text: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def cleanup(self):
        """Clean up resources before exit"""
        try:
            self.stop_translation()
            if self.translation_model:
                self.translation_model.cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
