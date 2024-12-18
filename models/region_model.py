import ctypes
import platform
import tkinter as tk
import logging
from typing import Optional, Tuple

# Set DPI awareness for Windows
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as dpi_error:
        logging.warning(f"Failed to set DPI awareness: {dpi_error}")

class RegionModel:
    def __init__(self):
        self.selected_region = None
        self._observers = []
        
    def add_observer(self, observer: callable):
        """Observer pattern: Add an observer to be notified of changes"""
        self._observers.append(observer)
        
    def notify_observers(self):
        """Notify all observers of a change"""
        for observer in self._observers:
            observer()
            
    def select_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Open region selector and return selected coordinates"""
        selector = RegionSelector()
        region = selector.get_region()
        if region:
            self.selected_region = region
            self.notify_observers()
        return region
        
    def get_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Get currently selected region"""
        return self.selected_region
        
    def clear_region(self):
        """Clear selected region"""
        self.selected_region = None
        self.notify_observers()

class RegionSelector:
    def __init__(self):
        self.root = tk.Toplevel()
        self.root.attributes('-alpha', 0.4)
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        
        # Remove window decorations
        self.root.overrideredirect(True)
        
        # State
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.selected_region = None
        
        # Screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Create canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Escape>", self.on_escape)
        
        # Set focus and grab
        self.root.focus_force()
        self.root.grab_set()
        
    def on_press(self, event):
        """Handle mouse press"""
        self.start_x = event.x
        self.start_y = event.y
        
        # Create selection rectangle
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline='red', width=2
        )
        
    def on_drag(self, event):
        """Handle mouse drag"""
        if self.start_x is not None and self.start_y is not None:
            # Update selection rectangle
            self.canvas.coords(
                self.current_rect,
                self.start_x, self.start_y,
                event.x, event.y
            )
            
    def on_release(self, event):
        """Handle mouse release"""
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
                
                # Release grab and close window
                self.root.grab_release()
                self.root.destroy()
            else:
                logging.warning("No valid starting coordinates found")
        except Exception as e:
            logging.error(f"Error in region selection: {e}")
            self.root.grab_release()
            self.root.destroy()
            
    def on_escape(self, _event):
        """Handle escape key"""
        self.selected_region = None
        self.root.grab_release()
        self.root.destroy()
        
    def get_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Get the selected region"""
        try:
            # Wait for window to be destroyed
            self.root.wait_window()
            return self.selected_region
        except Exception as e:
            logging.error(f"Error getting region: {e}")
            return None