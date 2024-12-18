import os
import logging
import numpy as np
import pytesseract
import easyocr
import torch
import winocr
from PIL import Image, ImageEnhance
import time
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OCRModel:
    def __init__(self):
        self._current_engine: str = 'Tesseract'
        self._observers: List[callable] = []
        self._available_engines = ["Tesseract", "EasyOCR", "Windows OCR"]
        
        # Initialize OCR manager
        self._ocr_manager = OCRManager()
            
    def add_observer(self, observer: callable):
        """Observer pattern: Add an observer to be notified of changes"""
        self._observers.append(observer)
        
    def notify_observers(self):
        """Notify all observers of a change"""
        for observer in self._observers:
            observer()
            
    async def process_image(self, image: Image.Image, lang: str = 'auto') -> Optional[str]:
        """Process image using current OCR engine"""
        try:
            return await self._ocr_manager.process_image(image, self._current_engine, lang)
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
        self._cached_results = {}  # Last OCR results
        self._cache_timeout = 5  # 5 second cache timeout
        
        tesseract_path = os.getenv('TESSERACT_PATH')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def get_easyocr_reader(self):
        if self._reader is None:
            try:
                # Suppress warnings
                import warnings
                warnings.filterwarnings('ignore')
                
                # Initialize with LSTM batch first
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                torch.backends.cudnn.enabled = False  # Disable CUDNN
                
                self._reader = easyocr.Reader(
                    ['en', 'tr'], 
                    gpu=(device=='cuda'),
                    model_storage_directory='model_storage',
                    download_enabled=True,
                    verbose=False,
                    quantize=True  # Reduce memory usage
                )
                
            except Exception as e:
                logging.error(f"EasyOCR initialization error: {e}")
                self._reader = None
                
        return self._reader

    def ensure_tesseract(self):
        if not self._tesseract_initialized:
            pytesseract.get_tesseract_version()
            self._tesseract_initialized = True

    async def process_image(self, image: Image.Image, method: str, source_lang: str = 'auto') -> str:
        try:
            # Create image hash
            image_hash = hash(image.tobytes())
            
            # If in cache and not expired, return from cache
            cache_key = (image_hash, method, source_lang)
            if cache_key in self._cached_results:
                cached_time, cached_result = self._cached_results[cache_key]
                if time.time() - cached_time < self._cache_timeout:
                    return cached_result

            # Perform OCR
            result = await self._perform_ocr(image, method, source_lang)
            
            # Cache the result
            self._cached_results[cache_key] = (time.time(), result)
            return result

        except Exception as e:
            logging.error(f"OCR error ({method}): {e}")
            return ""

    async def _perform_ocr(self, image: Image.Image, method: str, source_lang: str) -> str:
        """Perform OCR using specified method"""
        if method == "EasyOCR":
            try:
                if not self._reader:
                    self._reader = self.get_easyocr_reader()
                    
                # Convert PIL Image to numpy array
                image_np = np.array(image)
                
                # Get OCR results
                results = self._reader.readtext(image_np)
                
                # Calculate line groups based on vertical positions
                if not results:
                    return ""
                    
                # Calculate the average height of text blocks
                heights = [abs(box[0][3][1] - box[0][0][1]) for box in results]
                avg_height = sum(heights) / len(heights)
                line_threshold = avg_height * 0.5  # Threshold for considering text on same line
                
                # Group text blocks into lines
                lines = []
                current_line = []
                last_y = None
                
                # Sort initially by top y-coordinate
                sorted_by_y = sorted(results, key=lambda r: min(p[1] for p in r[0]))
                
                for result in sorted_by_y:
                    top_y = min(p[1] for p in result[0])
                    
                    if last_y is None or abs(top_y - last_y) <= line_threshold:
                        current_line.append(result)
                    else:
                        if current_line:
                            # Sort text blocks in the line by x-coordinate
                            current_line.sort(key=lambda r: min(p[0] for p in r[0]))
                            lines.append(current_line)
                        current_line = [result]
                    last_y = top_y
                
                # Don't forget the last line
                if current_line:
                    current_line.sort(key=lambda r: min(p[0] for p in r[0]))
                    lines.append(current_line)
                    
                # Combine all text maintaining the order
                text_lines = []
                for line in lines:
                    line_text = ' '.join(block[1] for block in line)
                    text_lines.append(line_text)
                
                text = ' '.join(text_lines)
                return self._fix_ocr_errors(text)
                
            except Exception as e:
                logging.error(f"EasyOCR processing error: {e}")
                return ""
            
        elif method == "Windows OCR":
            try:
                result = await winocr.recognize_pil(image, 'en' if source_lang == 'auto' else source_lang)
                if result and hasattr(result, 'text'):
                    return self._fix_ocr_errors(result.text.strip())
                return ""
            except Exception as e:
                logging.error(f"Windows OCR error: {e}")
                return ""
        
        else:  # Tesseract
            try:
                self.ensure_tesseract()
                text = pytesseract.image_to_string(image).strip()
                return self._fix_ocr_errors(text)
            except Exception as e:
                logging.error(f"Tesseract error: {e}")
                return ""
                
    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors in the text."""
        # Common replacements
        replacements = {
            '1 ': 'I ',  # Fix common "1" instead of "I" error
            ' 1 ': ' I ',  # Fix "1" surrounded by spaces
            ' i ': ' I ',  # Fix lowercase "i" as standalone pronoun
            ' im ': ' I\'m ',  # Fix common "im" error
            ' ill ': ' I\'ll ',  # Fix common "ill" error
            ' ive ': ' I\'ve ',  # Fix common "ive" error
            ' id ': ' I\'d ',  # Fix common "id" error
        }
        
        # Apply all replacements
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # Fix sentence starts
        sentences = text.split('. ')
        fixed_sentences = []
        for sentence in sentences:
            if sentence and sentence[0].islower():
                sentence = sentence[0].upper() + sentence[1:]
            fixed_sentences.append(sentence)
        
        return '. '.join(fixed_sentences)