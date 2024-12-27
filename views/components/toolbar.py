from typing import Any, Callable

import customtkinter as ctk


class Toolbar(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        on_select_region: Callable,
        on_start_translation: Callable,
        on_stop_translation: Callable,
        on_show_history: Callable,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self.on_select_region = on_select_region
        self.on_start_translation = on_start_translation
        self.on_stop_translation = on_stop_translation
        self.on_show_history = on_show_history

        self._is_translating = False
        self._create_widgets()

    def _create_widgets(self):
        """Create toolbar widgets"""
        # Region selection button
        self.region_btn = ctk.CTkButton(
            self,
            text="Select Region 📋",
            command=self.on_select_region,
            width=120,
        )
        self.region_btn.pack(side="left", padx=5)

        # Translation control button
        self.translation_btn = ctk.CTkButton(
            self,
            text="Start Translation ▶️",
            command=self._toggle_translation,
            width=120,
            state="disabled",
        )
        self.translation_btn.pack(side="left", padx=5)

        # History button
        self.history_btn = ctk.CTkButton(
            self, text="History 📜", command=self.on_show_history, width=120
        )
        self.history_btn.pack(side="right", padx=5)

    def _toggle_translation(self):
        """Toggle translation state"""
        if not self._is_translating:
            self._is_translating = True
            self.translation_btn.configure(
                text="Stop Translation ⏹️",
                fg_color=("#C42B2B", "#8B1F1F"),
                hover_color=("#A32424", "#701919"),
            )
            self.on_start_translation()
        else:
            self._is_translating = False
            self.translation_btn.configure(
                text="Start Translation ▶️",
                fg_color=("#2B5EA8", "#1F4475"),
                hover_color=("#234B85", "#193A5E"),
            )
            self.on_stop_translation()

    def enable_translation_button(self):
        """Enable translation button"""
        self.translation_btn.configure(state="normal")

    def disable_translation_button(self):
        """Disable translation button"""
        self.translation_btn.configure(state="disabled")

    def reset_translation_button(self):
        """Reset translation button state"""
        self.translation_btn.configure(
            text="Start Translation ▶️", command=self.on_start_translation
        )
