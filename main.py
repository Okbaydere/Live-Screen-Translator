import logging
import sys

import customtkinter as ctk

from controllers.main_controller import MainController


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s:%(message)s"
    )

    # Set DPI awareness for Windows
    if sys.platform == "win32":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            logging.warning(f"Failed to set DPI awareness: {e}")

    # Create root window
    root = ctk.CTk()

    # Create and run main controller
    controller = MainController(root)
    controller.run()


if __name__ == "__main__":
    main()
