import logging
from typing import Any, Callable

import customtkinter as ctk


class SettingsPanel(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        on_toggle_topmost: Callable,
        on_toggle_game_mode: Callable,
        on_change_opacity: Callable,
        on_change_translation_engine: Callable,
        on_change_ocr_engine: Callable,
        on_toggle_global_shortcuts: Callable,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        # Store callbacks
        self.on_toggle_topmost = on_toggle_topmost
        self.on_toggle_game_mode = on_toggle_game_mode
        self.on_change_opacity = on_change_opacity
        self.on_change_translation_engine = on_change_translation_engine
        self.on_change_ocr_engine = on_change_ocr_engine
        self.on_toggle_global_shortcuts = on_toggle_global_shortcuts

        # Create widgets
        self._create_widgets()

    def _create_widgets(self):
        """Create settings widgets"""
        # Create tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)

        # Add tabs
        self.tabview.add("General")
        self.tabview.add("Translation")
        self.tabview.add("Appearance")

        self._create_general_tab()
        self._create_translation_tab()
        self._create_appearance_tab()

    def _create_general_tab(self):
        """Create general settings tab"""
        tab = self.tabview.tab("General")

        # Window settings
        window_frame = ctk.CTkFrame(tab)
        window_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(window_frame, text="Window Settings").pack(
            anchor="w", padx=5, pady=2
        )

        # Always on top
        self.topmost_var = ctk.BooleanVar(value=True)
        topmost_switch = ctk.CTkSwitch(
            window_frame,
            text="Always on Top",
            variable=self.topmost_var,
            command=lambda: self.on_toggle_topmost(self.topmost_var.get()),
        )
        topmost_switch.pack(anchor="w", padx=5, pady=2)

        # Game mode
        self.game_mode_var = ctk.BooleanVar(value=False)
        game_mode_switch = ctk.CTkSwitch(
            window_frame,
            text="Game Mode",
            variable=self.game_mode_var,
            command=lambda: self.on_toggle_game_mode(self.game_mode_var.get()),
        )
        game_mode_switch.pack(anchor="w", padx=5, pady=2)

        # Global shortcuts
        self.global_shortcuts_var = ctk.BooleanVar(value=True)
        shortcuts_switch = ctk.CTkSwitch(
            window_frame,
            text="Global Shortcuts",
            variable=self.global_shortcuts_var,
            command=lambda: self.on_toggle_global_shortcuts(
                self.global_shortcuts_var.get()
            ),
        )
        shortcuts_switch.pack(anchor="w", padx=5, pady=2)

    def _create_translation_tab(self):
        """Create translation settings tab"""
        tab = self.tabview.tab("Translation")

        # Translation engine
        engine_frame = ctk.CTkFrame(tab)
        engine_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(engine_frame, text="Translation Engine").pack(
            anchor="w", padx=5, pady=2
        )

        self.translation_engine = ctk.StringVar(value="Gemini")
        engines = ["Gemini", "Google Translate", "Local API"]

        def create_translation_command(engine_name: str):
            def command():
                try:
                    # Disable all radio buttons temporarily
                    for btn in engine_frame.winfo_children():
                        if isinstance(btn, ctk.CTkRadioButton):
                            btn.configure(state="disabled")

                    # Call the handler
                    self.on_change_translation_engine(engine_name)

                    # Re-enable radio buttons after a delay
                    self.after(
                        500,
                        lambda: [
                            radio_btn.configure(state="normal")
                            for radio_btn in engine_frame.winfo_children()
                            if isinstance(radio_btn, ctk.CTkRadioButton)
                        ],
                    )
                except Exception as e:
                    logging.error(f"Error in translation engine change: {e}")

            return command

        for engine in engines:
            ctk.CTkRadioButton(
                engine_frame,
                text=engine,
                variable=self.translation_engine,
                value=engine,
                command=create_translation_command(engine),
            ).pack(anchor="w", padx=5, pady=2)

        # OCR engine
        ocr_frame = ctk.CTkFrame(tab)
        ocr_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(ocr_frame, text="OCR Engine").pack(
            anchor="w", padx=5, pady=2
        )

        self.ocr_engine = ctk.StringVar(value="Tesseract")
        ocr_engines = ["Tesseract", "EasyOCR", "Windows OCR"]

        def create_ocr_command(engine_name: str):
            def command():
                try:
                    # Disable all radio buttons temporarily
                    for btn in ocr_frame.winfo_children():
                        if isinstance(btn, ctk.CTkRadioButton):
                            btn.configure(state="disabled")

                    # Call the handler
                    self.on_change_ocr_engine(engine_name)

                    # Re-enable radio buttons after a delay
                    self.after(
                        500,
                        lambda: [
                            radio_btn.configure(state="normal")
                            for radio_btn in ocr_frame.winfo_children()
                            if isinstance(radio_btn, ctk.CTkRadioButton)
                        ],
                    )
                except Exception as e:
                    logging.error(f"Error in OCR engine change: {e}")

            return command

        for engine in ocr_engines:
            ctk.CTkRadioButton(
                ocr_frame,
                text=engine,
                variable=self.ocr_engine,
                value=engine,
                command=create_ocr_command(engine),
            ).pack(anchor="w", padx=5, pady=2)

    def _create_appearance_tab(self):
        """Create appearance settings tab"""
        tab = self.tabview.tab("Appearance")

        # Opacity settings
        opacity_frame = ctk.CTkFrame(tab)
        opacity_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(opacity_frame, text="Window Opacity").pack(
            anchor="w", padx=5, pady=2
        )

        self.opacity_label = ctk.CTkLabel(opacity_frame, text="90%")
        self.opacity_label.pack(anchor="w", padx=5)

        opacity_slider = ctk.CTkSlider(
            opacity_frame,
            from_=20,
            to=100,
            number_of_steps=80,
            command=self._on_opacity_change,
        )
        opacity_slider.set(90)
        opacity_slider.pack(fill="x", padx=5, pady=2)

    def _on_opacity_change(self, value: float):
        """Handle opacity slider change"""
        percentage = int(value)
        self.opacity_label.configure(text=f"{percentage}%")
        self.on_change_opacity(percentage / 100)

    def cleanup(self):
        """Clean up resources"""
        pass  # Add cleanup code if needed
