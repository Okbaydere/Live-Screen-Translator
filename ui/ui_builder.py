import customtkinter as ctk

class UIBuilder:
    """UI bileşenleri oluşturmak için yardımcı sınıf."""

    def __init__(self, root):
        self.root = root

    def create_frame(self, parent, **kwargs):
        return ctk.CTkFrame(parent, **kwargs)

    def create_label(self, parent, **kwargs):
        return ctk.CTkLabel(parent, **kwargs)

    def create_button(self, parent, **kwargs):
        return ctk.CTkButton(parent, **kwargs)

    def create_switch(self, parent, **kwargs):
        return ctk.CTkSwitch(parent, **kwargs)

    def create_slider(self, parent, **kwargs):
        return ctk.CTkSlider(parent, **kwargs)

    def create_combobox(self, parent, **kwargs):
        return ctk.CTkComboBox(parent, **kwargs)

    def create_scrollable_frame(self, parent, **kwargs):
        return ctk.CTkScrollableFrame(parent, **kwargs)