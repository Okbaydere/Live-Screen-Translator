from typing import Protocol, Union

import customtkinter as ctk

try:
    from CTkMessagebox import CTkMessagebox
    MessageBox = CTkMessagebox
except ImportError:
    # Fallback to basic messagebox if CTkMessagebox is not available
    class CTkMessageboxFallback:
        def __init__(self, **kwargs):
            dialog = ctk.CTkInputDialog(
                text=kwargs.get("message", ""),
                title=kwargs.get("title", "Message"),
            )
            dialog.geometry("400x200")

            # Hide the input field since we only want to show a message
            for child in dialog.winfo_children():
                if isinstance(child, ctk.CTkEntry):
                    child.pack_forget()

            # Add an OK button
            ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack(
                pady=10
            )
    MessageBox = CTkMessageboxFallback


class MainViewProtocol(Protocol):
    """Protocol defining the interface for main view callbacks"""

    def on_select_region(self): ...
    def on_start_translation(self): ...
    def on_stop_translation(self): ...
    def on_show_history(self): ...
    def on_change_translation_engine(self, engine: str): ...
    def on_change_ocr_engine(self, engine: str): ...
    def on_toggle_global_shortcuts(self, enabled: bool): ...
    def on_change_source_language(self, language: str): ...
    def on_change_target_language(self, language: str): ...
    def on_toggle_game_mode(self, enabled: bool): ...
    def on_toggle_topmost(self, enabled: bool): ...
    def on_change_opacity(self, value: float): ...


class MainView:
    def __init__(self, root: ctk.CTk, controller: MainViewProtocol):
        self.root = root
        self.controller = controller

        # Create main layout
        self._create_layout()

        # Create components
        self._create_components()

    def _create_layout(self):
        """Create the main window layout"""
        # Main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Create scrollable control panel (left side)
        self.control_panel = ctk.CTkScrollableFrame(
            self.main_container, width=250, label_text="Controls & Settings"
        )
        self.control_panel.pack(
            side="left", fill="y", padx=(0, 5), expand=False
        )

        # Status panel (right side)
        self.status_panel = ctk.CTkFrame(self.main_container)
        self.status_panel.pack(
            side="right", fill="both", expand=True, padx=(5, 0)
        )

    def _create_components(self):
        """Create UI components"""
        self._create_control_panel()
        self._create_status_panel()

    @staticmethod
    def _create_section_frame(
        parent: Union[ctk.CTkFrame, ctk.CTkScrollableFrame], title: str
    ) -> ctk.CTkFrame:
        """Create a section frame with title"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=5)

        if title:
            ctk.CTkLabel(frame, text=title, font=("Arial", 12, "bold")).pack(
                anchor="w", padx=5, pady=2
            )

        return frame

    @staticmethod
    def _create_labeled_option_menu(
        parent: Union[ctk.CTkFrame, ctk.CTkScrollableFrame],
        label: str,
        variable: ctk.StringVar,
        values: list[str],
        command,
        width: int = 120,
    ) -> ctk.CTkOptionMenu:
        """Create a labeled option menu"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=2)

        ctk.CTkLabel(frame, text=label).pack(side="left", padx=5)
        menu = ctk.CTkOptionMenu(
            frame,
            variable=variable,
            values=values,
            command=command,
            width=width,
        )
        menu.pack(side="right", padx=5)
        return menu

    @staticmethod
    def _create_shortcut_label(
        parent: Union[ctk.CTkFrame, ctk.CTkScrollableFrame],
        key: str,
        description: str,
    ) -> ctk.CTkLabel:
        """Create a shortcut label with consistent formatting"""
        return ctk.CTkLabel(
            parent,
            text=f"{key:<15} - {description}",
            font=("Arial", 11),
            justify="left",
        )

    @staticmethod
    def _create_status_label(
        parent: Union[ctk.CTkFrame, ctk.CTkScrollableFrame],
        text: str,
        text_color: str | tuple = "gray",
    ) -> ctk.CTkLabel:
        """Create a status label with consistent formatting"""
        return ctk.CTkLabel(parent, text=text, text_color=text_color)

    def _create_control_panel(self):
        """Create control panel with buttons and settings"""
        # Main Controls Section
        main_controls = self._create_section_frame(self.control_panel, "")

        # Region selection and translation buttons
        self.region_btn = ctk.CTkButton(
            main_controls,
            text="Select Region 📋",
            command=self.controller.on_select_region,
        )
        self.region_btn.pack(fill="x", padx=5, pady=5)

        self.translation_btn = ctk.CTkButton(
            main_controls,
            text="Start Translation ▶️",
            command=self.controller.on_start_translation,
            state="disabled",
        )
        self.translation_btn.pack(fill="x", padx=5, pady=5)

        # Window Settings Section
        window_frame = self._create_section_frame(
            self.control_panel, "Window Settings"
        )

        # Create a sub-frame for switches
        switches_frame = ctk.CTkFrame(window_frame)
        switches_frame.pack(fill="x", padx=5, pady=2)

        # Put switches side by side
        self.game_mode_var = ctk.BooleanVar(value=False)
        game_mode_switch = ctk.CTkSwitch(
            switches_frame,
            text="Game Mode",
            variable=self.game_mode_var,
            command=lambda: self.controller.on_toggle_game_mode(
                self.game_mode_var.get()
            ),
        )
        game_mode_switch.pack(side="left", padx=5)

        self.topmost_var = ctk.BooleanVar(value=True)
        topmost_switch = ctk.CTkSwitch(
            switches_frame,
            text="Top Most",
            variable=self.topmost_var,
            command=lambda: self.controller.on_toggle_topmost(
                self.topmost_var.get()
            ),
        )
        topmost_switch.pack(side="left", padx=5)

        # Opacity slider
        opacity_frame = ctk.CTkFrame(window_frame)
        opacity_frame.pack(fill="x", padx=5, pady=2)

        ctk.CTkLabel(opacity_frame, text="Opacity").pack(side="left", padx=5)
        self.opacity_var = ctk.DoubleVar(value=0.9)
        opacity_slider = ctk.CTkSlider(
            opacity_frame,
            from_=10,  # 10% minimum
            to=100,  # 100% maximum
            variable=None,  # Don't bind directly to avoid type issues
            command=self._on_opacity_change,
        )
        opacity_slider.set(
            self.opacity_var.get() * 100
        )  # Convert to percentage
        opacity_slider.pack(side="left", fill="x", expand=True, padx=5)

        # Language Settings Section
        lang_frame = self._create_section_frame(
            self.control_panel, "Language Settings"
        )

        # Source language
        self.source_lang = ctk.StringVar(value="auto")
        self._create_labeled_option_menu(
            lang_frame,
            "Source:",
            self.source_lang,
            ["auto", "en", "ja", "ko", "zh", "tr", "fr", "de", "es", "it"],
            self.controller.on_change_source_language,
        )

        # Target language
        self.target_lang = ctk.StringVar(value="en")
        self._create_labeled_option_menu(
            lang_frame,
            "Target:",
            self.target_lang,
            ["en", "ja", "ko", "zh", "tr", "fr", "de", "es", "it"],
            self.controller.on_change_target_language,
        )

        # Engine Settings Section
        engine_frame = self._create_section_frame(
            self.control_panel, "Engine Settings"
        )

        # Translation engine
        self.translation_engine = ctk.StringVar(value="Gemini")
        self._create_labeled_option_menu(
            engine_frame,
            "Translator:",
            self.translation_engine,
            ["Gemini", "Google Translate", "Local API"],
            self.controller.on_change_translation_engine,
        )

        # OCR engine
        self.ocr_engine = ctk.StringVar(value="Tesseract")
        self._create_labeled_option_menu(
            engine_frame,
            "OCR:",
            self.ocr_engine,
            ["Tesseract", "EasyOCR", "Windows OCR"],
            self.controller.on_change_ocr_engine,
        )

        # Additional Settings Section
        additional_frame = self._create_section_frame(
            self.control_panel, "Additional Settings"
        )

        self.shortcuts_var = ctk.BooleanVar(value=True)
        shortcuts_switch = ctk.CTkSwitch(
            additional_frame,
            text="Global Shortcuts",
            variable=self.shortcuts_var,
            command=lambda: self.controller.on_toggle_global_shortcuts(
                self.shortcuts_var.get()
            ),
        )
        shortcuts_switch.pack(anchor="w", padx=5, pady=5)

        # History button at the bottom
        history_frame = self._create_section_frame(self.control_panel, "")

        self.history_btn = ctk.CTkButton(
            history_frame,
            text="View History 📜",
            command=self.controller.on_show_history,
        )
        self.history_btn.pack(fill="x", padx=5, pady=5)

    def _create_status_panel(self):
        """Create status panel with information display"""
        # Status labels
        status_frame = ctk.CTkFrame(self.status_panel)
        status_frame.pack(fill="x", padx=5, pady=5)

        self.region_status = self._create_status_label(
            status_frame, "❌ No region selected", ("#C42B2B", "#8B1F1F")
        )
        self.region_status.pack(anchor="w", padx=5, pady=2)

        self.translation_status = self._create_status_label(
            status_frame, "Translation: Idle", "gray"
        )
        self.translation_status.pack(anchor="w", padx=5, pady=2)

        # Shortcuts info
        shortcuts_frame = ctk.CTkFrame(self.status_panel)
        shortcuts_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            shortcuts_frame,
            text="Keyboard Shortcuts",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", padx=5, pady=(5, 2))

        shortcuts = [
            ("Ctrl + Space", "Start/Stop Translation"),
            ("Ctrl + R", "Select Region"),
            ("Ctrl + T", "Change Translation Engine"),
            ("Ctrl + O", "Change OCR Engine"),
            ("Ctrl + H", "Show History"),
        ]

        for key, description in shortcuts:
            shortcut_label = self._create_shortcut_label(
                shortcuts_frame, key, description
            )
            shortcut_label.pack(anchor="w", padx=5, pady=1)

        # Toast notification
        self.toast_label = self._create_status_label(status_frame, "", "gray")
        self.toast_label.pack(anchor="w", padx=5, pady=2)

    def update_region_status(self, text: str, color: tuple):
        """Update region selection status"""
        self.region_status.configure(text=text, text_color=color)

    def update_translation_status(self, text: str, color: tuple):
        """Update translation status"""
        self.translation_status.configure(text=text, text_color=color)

    def show_error(self, title: str, message: str):
        """Show error dialog"""
        MessageBox(
            master=self.root,
            title=title,
            message=message,
            icon="cancel",
            option_1="OK",
        )

    def show_toast(self, message: str):
        """Show a temporary notification message"""
        self.toast_label.configure(text=message)
        self.root.after(2000, lambda: self.toast_label.configure(text=""))

    def enable_translation_button(self):
        """Enable translation button"""
        self.translation_btn.configure(state="normal")

    def disable_translation_button(self):
        """Disable translation button"""
        self.translation_btn.configure(state="disabled")

    def set_translation_button_state(self, is_translating: bool):
        """Update translation button state"""
        if is_translating:
            self.translation_btn.configure(
                text="Stop Translation ⏹️",
                command=self.controller.on_stop_translation,
                fg_color=("#C42B2B", "#8B1F1F"),
                hover_color=("#A32424", "#701919"),
            )
        else:
            self.translation_btn.configure(
                text="Start Translation ▶️",
                command=self.controller.on_start_translation,
                fg_color=("#2B5EA8", "#1F4475"),
                hover_color=("#234B85", "#193A5E"),
            )

    def cleanup(self):
        """Clean up resources"""
        pass

    def _on_opacity_change(self, value: float):
        """Handle opacity slider change"""
        opacity = float(value) / 100  # Convert percentage to 0-1 range
        self.opacity_var.set(opacity)
        self.controller.on_change_opacity(opacity)
