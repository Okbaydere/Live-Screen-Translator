import ctypes
import platform
import tkinter as tk
import logging
import traceback

# Set DPI awareness for Windows
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as dpi_error:
        logging.warning(f"Failed to set DPI awareness: {dpi_error}")

class RegionSelector:
    def __init__(self):
        # Create transparent window
        self.root = tk.Toplevel()
        
        # Get screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Configure window
        self.root.attributes(
            '-fullscreen', True,
            '-alpha', 0.3,
            '-topmost', True
        )
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.root.title("Select Screen Region")

        # Transparent canvas that covers entire screen
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            highlightthickness=0,
            cursor='cross',
            bg='white'  # Add white background
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Semi-transparent selection rectangle
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.selected_region = None

        # Setup event bindings
        self.setup_bindings()

        # Logging
        logging.info("RegionSelector initialized")

    def setup_bindings(self):
        # Bind mouse events
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

        # Escape key to cancel
        self.root.bind('<Escape>', self.on_escape)

    def on_press(self, event):
        try:
            # Reset any existing selection
            if self.rect:
                self.canvas.delete(self.rect)

            # Store starting coordinates
            self.start_x = event.x
            self.start_y = event.y

            # Create initial selection rectangle
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y,
                self.start_x, self.start_y,
                outline='red',
                width=2
            )
        except Exception as press_error:
            logging.error(f"Error in on_press: {press_error}")
            logging.error(traceback.format_exc())

    def on_drag(self, event):
        try:
            # Update rectangle as user drags
            if self.rect:
                self.canvas.coords(
                    self.rect,
                    self.start_x, self.start_y,
                    event.x, event.y
                )
        except Exception as drag_error:
            logging.error(f"Error in on_drag: {drag_error}")
            logging.error(traceback.format_exc())

    def on_release(self, event):
        try:
            # Validate region size
            if self.start_x is not None and self.start_y is not None:
                # Check if the entire screen is selected
                if (self.start_x == 0 and self.start_y == 0 and
                        event.x == self.screen_width and event.y == self.screen_height):
                    # Select the entire screen
                    self.selected_region = (0, 0, self.screen_width, self.screen_height)
                    logging.info("Entire screen selected")
                elif (abs(event.x - self.start_x) > 10 and
                      abs(event.y - self.start_y) > 10):
                    # Store selected region coordinates
                    self.selected_region = (
                        min(self.start_x, event.x),  # left
                        min(self.start_y, event.y),  # top
                        max(self.start_x, event.x),  # right
                        max(self.start_y, event.y)   # bottom
                    )
                    logging.info(f"Region selected: {self.selected_region}")

                # Close the selection window
                self.root.destroy()
            else:
                logging.warning("No valid starting coordinates found")
        except Exception as release_error:
            logging.error(f"Error in on_release: {release_error}")
            logging.error(traceback.format_exc())

    def on_escape(self, _event):
        # Cancel selection
        logging.info("Region selection cancelled")
        self.selected_region = None
        self.root.destroy()

    def get_region(self):
        try:
            # Make the window modal
            self.root.grab_set()
            self.root.focus_force()

            # Wait for window to be destroyed
            self.root.wait_window()

            return self.selected_region
        except Exception as region_error:
            logging.error(f"Error in get_region: {region_error}")
            logging.error(traceback.format_exc())
            return None