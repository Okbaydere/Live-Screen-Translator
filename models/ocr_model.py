import logging
import os
import time
from typing import Callable, List, Optional

import easyocr
import numpy as np
import pytesseract
import torch
import winocr
from dotenv import load_dotenv
from PIL import Image, ImageEnhance
from cachetools import TTLCache

# Load environment variables
load_dotenv()

# Başlangıçta loglama konfigürasyonu
logging.basicConfig(level=logging.ERROR)


class OCRModel:
    def __init__(self):
        self._current_engine: str = "Tesseract"
        self._observers: List[Callable] = []
        self._available_engines = ["Tesseract", "EasyOCR", "Windows OCR"]

        # Initialize OCR manager
        self._ocr_manager = OCRManager()

    def add_observer(self, observer: Callable):
        """Observer pattern: Add an observer to be notified of changes"""
        self._observers.append(observer)

    def notify_observers(self):
        """Notify all observers of a change"""
        for observer in self._observers:
            observer()

    async def process_image(
        self, image: Image.Image, lang: str = "auto", subtitle_mode: bool = True
    ) -> Optional[str]:
        """Process image using current OCR engine"""
        try:
            return await self._ocr_manager.process_image(
                image, self._current_engine, lang, subtitle_mode
            )
        except Exception as e:
            logging.error(f"OCR processing error: {e}")
            raise

    def set_engine(self, engine_name: str):
        """Change OCR engine"""
        if engine_name in self._available_engines:
            self._current_engine = engine_name
            self.notify_observers()
        else:
            raise ValueError(f"Unknown OCR engine: {engine_name}")

    def get_current_engine(self) -> str:
        """Get current OCR engine name"""
        return self._current_engine

    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engines"""
        return self._available_engines.copy()

    def cycle_engine(self) -> str:
        """Cycle to next OCR engine"""
        current_index = self._available_engines.index(self._current_engine)
        next_index = (current_index + 1) % len(self._available_engines)
        next_engine = self._available_engines[next_index]
        self.set_engine(next_engine)
        return next_engine


class OCRManager:
    def __init__(self):
        self._reader = None
        self._tesseract_initialized = False
        self._cache = TTLCache(maxsize=100, ttl=5)

        tesseract_path = os.getenv("TESSERACT_PATH")
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def get_easyocr_reader(self):
        if self._reader is None:
            try:
                # Suppress warnings
                import warnings

                warnings.filterwarnings("ignore")

                # Initialize with LSTM batch first
                device = "cuda" if torch.cuda.is_available() else "cpu"
                torch.backends.cudnn.enabled = False  # Disable CUDNN

                self._reader = easyocr.Reader(
                    ["en", "tr"],
                    gpu=(device == "cuda"),
                    model_storage_directory="model_storage",
                    download_enabled=True,
                    verbose=False,  # Reduce memory usage
                )

            except Exception as e:
                logging.error(f"EasyOCR initialization error: {e}")
                self._reader = None

        return self._reader

    def ensure_tesseract(self):
        if not self._tesseract_initialized:
            try:
                pytesseract.get_tesseract_version()
                self._tesseract_initialized = True
            except Exception as e:
                logging.error(f"Tesseract initialization error: {e}")

    async def process_image(
        self, image: Image.Image, method: str, source_lang: str = "auto", subtitle_mode: bool = True
    ) -> str:
        try:
            # Create image hash for caching
            image_hash = hash((image.tobytes(), subtitle_mode))
            cache_key = (image_hash, method, source_lang)

            if cache_key in self._cache:
                return self._cache[cache_key]

            # Preprocess image for subtitles conditionally
            processed_image = self._preprocess_image_for_subtitles(image, subtitle_mode)

            # Perform OCR
            result = await self._perform_ocr(processed_image, method, source_lang)

            self._cache[cache_key] = result
            return result

        except Exception as e:
            logging.error(f"OCR error ({method}): {e}")
            return ""

    def _preprocess_image_for_subtitles(self, image: Image.Image, subtitle_mode: bool) -> Image.Image:
        """Preprocess the image to better detect subtitles."""
        if not subtitle_mode:
            return image  # No preprocessing for full screen OCR

        try:
            # Convert to grayscale
            grayscale_image = image.convert("L")
            
            # Enhance contrast with more conservative values
            enhancer = ImageEnhance.Contrast(grayscale_image)
            enhanced_image = enhancer.enhance(1.5)  # Reduced from 2.0 to 1.5
            
            # Apply adaptive thresholding instead of fixed threshold
            threshold = self._calculate_adaptive_threshold(enhanced_image)
            binary_image = enhanced_image.point(lambda p: 255 if p > threshold else 0)
            
            return binary_image
            
        except Exception as e:
            logging.error(f"Error preprocessing image: {e}")
            return image  # Return original image if preprocessing fails

    def _calculate_adaptive_threshold(self, image: Image.Image) -> int:
        """Calculate adaptive threshold based on image content"""
        # Convert image to numpy array for calculations
        img_array = np.array(image)
        
        # Calculate mean and standard deviation
        mean = np.mean(img_array)
        std = np.std(img_array)
        
        # Adaptive threshold based on image statistics
        threshold = mean + 0.5 * std
        
        # Ensure threshold is within valid range
        return int(max(min(threshold, 200), 100))

    async def _perform_ocr(
        self, image: Image.Image, method: str, source_lang: str
    ) -> str:
        """Perform OCR using specified method"""
        try:
            if method == "EasyOCR":
                return await self._perform_easyocr(image)
            elif method == "Windows OCR":
                return await self._perform_windows_ocr(image, source_lang)
            else:
                return self._perform_tesseract_ocr(image, source_lang)
        except Exception as e:
            logging.error(f"{method} OCR error: {e}")
            return ""

    async def _perform_easyocr(self, image: Image.Image) -> str:
        """Perform OCR using EasyOCR"""
        if not self._reader:
            self._reader = self.get_easyocr_reader()

        image_np = np.array(image)
        results = self._reader.readtext(image_np)
        return OCRManager._process_easyocr_results(results)

    @staticmethod
    def _process_easyocr_results(results: List) -> str:
        """Process EasyOCR results into text, preserving line breaks."""
        if not results:
            return ""

        # Sort results by y-coordinate
        results.sort(key=lambda x: x[0][0][1])

        lines = []
        current_line = ""
        last_y_center = -1

        for bbox, text, confidence in results:
            y_centers = [coord[1] for coord in bbox]
            current_y_center = sum(y_centers) / len(y_centers)
            text = text.strip()

            if not current_line:
                current_line += text
                last_y_center = current_y_center
            elif abs(current_y_center - last_y_center) < 10:
                current_line += " " + text
            else:
                lines.append(current_line)
                current_line = text
                last_y_center = current_y_center

        if current_line:
            lines.append(current_line)

        return "\n".join(lines)

    @staticmethod
    def _calculate_line_threshold(results: List) -> float:
        """Calculate threshold for considering text blocks on the same line"""
        heights = [abs(box[0][3][1] - box[0][0][1]) for box in results]
        avg_height = sum(heights) / len(heights) if heights else 0
        return avg_height * 0.5

    @staticmethod
    def _get_block_y_position(block) -> float:
        """Get the top Y position of a text block"""
        return min(p[1] for p in block[0])

    @staticmethod
    def _get_block_x_position(block) -> float:
        """Get the left X position of a text block"""
        return min(p[0] for p in block[0])

    @staticmethod
    def _should_add_to_current_line(
        top_y: float, last_y: Optional[float], threshold: float
    ) -> bool:
        """Determine if a block should be added to the current line"""
        return last_y is None or abs(top_y - last_y) <= threshold

    @staticmethod
    def _sort_line_by_x_position(line: List) -> List:
        """Sort text blocks in a line by X position"""
        return sorted(line, key=OCRManager._get_block_x_position)

    @staticmethod
    def _group_text_blocks(results: List) -> List[List]:
        """Group text blocks into lines based on vertical position"""
        if not results:
            return []

        # Calculate line height threshold
        line_threshold = OCRManager._calculate_line_threshold(results)

        # Sort blocks by vertical position
        sorted_by_y = sorted(results, key=OCRManager._get_block_y_position)

        lines = []
        current_line = []
        last_y = None

        # Group blocks into lines
        for block in sorted_by_y:
            top_y = OCRManager._get_block_y_position(block)

            if OCRManager._should_add_to_current_line(
                top_y, last_y, line_threshold
            ):
                current_line.append(block)
            else:
                if current_line:
                    lines.append(
                        OCRManager._sort_line_by_x_position(current_line)
                    )
                current_line = [block]
            last_y = top_y

        # Add the last line if it exists
        if current_line:
            lines.append(OCRManager._sort_line_by_x_position(current_line))

        return lines

    async def _perform_windows_ocr(
        self, image: Image.Image, source_lang: str
    ) -> str:
        """Perform OCR using Windows OCR"""
        result = await winocr.recognize_pil(
            image, "en" if source_lang == "auto" else source_lang
        )
        if result and hasattr(result, "text"):
            return self._fix_ocr_errors(result.text.strip())
        return ""

    def _perform_tesseract_ocr(
        self, image: Image.Image, source_lang: str
    ) -> str:
        try:
            self.ensure_tesseract()
            lang = "eng" if source_lang == "auto" else source_lang
            
            # Use PSM 3 for automatic page segmentation
            # PSM modes:
            # 3 = Fully automatic page segmentation, but no OSD (default)
            # 6 = Assume a uniform block of text
            config = r'--psm 3 --oem 1'
            
            text = pytesseract.image_to_string(
                image,
                lang=lang,
                config=config
            ).strip()
            
            return self._fix_ocr_errors(text)
        except Exception as e:
            logging.error(f"Tesseract OCR error: {e}")
            return ""

    @staticmethod
    def _fix_ocr_errors(text: str) -> str:
        """Fix common OCR errors in the text."""
       

        # Fix sentence starts
        sentences = text.split(". ")
        fixed_sentences = []
        for sentence in sentences:
            if sentence and sentence[0].islower():
                sentence = sentence[0].upper() + sentence[1:]
            fixed_sentences.append(sentence)

        return ". ".join(fixed_sentences)

    def _initialize_easyocr_reader(self):
        """Initializes EasyOCR reader with configurations."""
        try:
            # Suppress warnings
            import warnings
            warnings.filterwarnings("ignore")

            # Initialize with LSTM batch first
            device = "cuda" if torch.cuda.is_available() else "cpu"
            torch.backends.cudnn.enabled = False  # Disable CUDNN

            self._reader = easyocr.Reader(
                ["en", "tr"],
                gpu=(device == "cuda"),
                model_storage_directory="model_storage",
                download_enabled=True,
                verbose=False,
                quantize=True,  # Reduce memory usage
            )

        except Exception as e:
            logging.error(f"EasyOCR initialization error: {e}")
            self._reader = None

    def _get_easyocr_reader(self):
        return self._reader

    def _set_easyocr_reader(self, reader):
        self._reader = reader




