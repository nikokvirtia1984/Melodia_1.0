from PyQt6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QLabel
from PyQt6.uic import loadUi
from typing import List
from paths import ui as ui_path


class InfoDialog(QDialog):
    def __init__(self, translated_attributes: List[str], material_name: str, parent=None):
        super().__init__(parent)

        # Load the dialog UI onto THIS new QDialog instance
        loadUi(ui_path('info_window.ui'), self)
        self.setWindowTitle(f"თვისებები: {material_name}")

        # --- Assumption ---
        # We assume your 'info_window.ui' contains a QLabel named 'product_name_label'
        # and a QListWidget or QTextEdit named 'attribute_list_widget' (or similar)

        # Display the product name
        self.product_name_label.setText(f"პროდუქტი: {material_name}")

        # Clear and populate the attribute list
        # Check if the widget exists (it must be defined in info_window.ui)
        if hasattr(self, 'attribute_list_widget') and isinstance(self.attribute_list_widget, QListWidget):
            self.attribute_list_widget.clear()
            for attr in translated_attributes:
                item = QListWidgetItem(attr)
                self.attribute_list_widget.addItem(item)
        else:
            print("WARNING: attribute_list_widget not found or is wrong type in info_window.ui")