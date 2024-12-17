import sys
import logging
import traceback
from ui.app_core import AppCore

def main():
    try:
        app = AppCore()
        app.run()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        logging.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 