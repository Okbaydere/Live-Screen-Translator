import os
import logging
import numpy as np
import pytesseract
import easyocr
import torch
import winocr
from PIL import Image
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OCRManager:
    def __init__(self):
        self.reader = None
        self._tesseract_initialized = False
        self._cached_results = {}  # Last OCR results
        self._cache_timeout = 5  # 5 second cache timeout
        
        tesseract_path = os.getenv('TESSERACT_PATH')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def get_easyocr_reader(self):
        if self.reader is None:
            try:
                # Suppress warnings
                import warnings
                warnings.filterwarnings('ignore')
                
                # Initialize with LSTM batch first
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                torch.backends.cudnn.enabled = False  # Disable CUDNN
                
                self.reader = easyocr.Reader(
                    ['en', 'tr'], 
                    gpu=(device=='cuda'),
                    model_storage_directory='model_storage',
                    download_enabled=True,
                    verbose=False,
                    quantize=True  # Reduce memory usage
                )
                
            except Exception as e:
                logging.error(f"EasyOCR initialization error: {e}")
                self.reader = None
                
        return self.reader

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

    async def _perform_ocr(self, image, method, source_lang):
        if method == "EasyOCR":
            self.reader = self.get_easyocr_reader()
            
            # Convert PIL Image to numpy array
            img_np = np.array(image)
            
            # Enhance image for better OCR
            from PIL import ImageEnhance, Image
            image = Image.fromarray(img_np)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)
            
            # Convert back to numpy array
            img_np = np.array(image)
            
            # Use supported parameters for better accuracy
            results = self.reader.readtext(
                img_np,
                decoder='greedy',  # Use greedy decoder for better single character detection
                batch_size=4,
                detail=1,
                contrast_ths=0.3,  # Adjust contrast threshold
                adjust_contrast=1.0,  # Don't adjust contrast in readtext since we did it in preprocessing
                text_threshold=0.5,  # Lower threshold for better character detection
                low_text=0.3,  # Lower threshold for text detection
                mag_ratio=2  # Increase image size for better small text detection
            )
            
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
            
            # Post-process the text to fix common OCR errors
            text = self._fix_ocr_errors(text)
            
            return text
            
        elif method == "Windows OCR":
            result = await winocr.recognize_pil(image, 'en' if source_lang == 'auto' else source_lang)
            return result.text
        
        else:  # Tesseract
            self.ensure_tesseract()
            return pytesseract.image_to_string(image)
            
    def _fix_ocr_errors(self, text):
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