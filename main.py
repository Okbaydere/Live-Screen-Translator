import logging
import traceback
from ui.screen_translator import ScreenTranslator

def main():
    try:
        translator = ScreenTranslator()
        translator.run()
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        logging.critical(traceback.format_exc())
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 