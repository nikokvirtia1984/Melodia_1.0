from PyQt6.QtCore import QModelIndex, QFile, QIODevice, QTextStream, Qt, QEvent
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (QWidget, QMessageBox, QLineEdit, QComboBox, QTextEdit, QTableWidget, QCheckBox, QTableView, QHeaderView, QApplication)
from PyQt6.uic import loadUi
import random
import psycopg2
import datetime
import os
import pathlib
from typing import List, Union, Dict, Any
import logging
import jinja2
import pdfkit
import re

# --- Local Project Imports ---
from user_system import UserSystem
from database import Database
from att_mat import MaterialAttributeTranslator
from return_function import ReturnProduct
from info_dialog import InfoDialog
from generic import CodeGeneric

# --- GLOBAL DEFINITIONS ---
db = Database()
attmat = MaterialAttributeTranslator()
VAT_RATE = 0.18  # Define the VAT rate (18%)


# --------------------------


class MerchantTable(QWidget):
    def __init__(self, parent=None, current_username=''):
        super().__init__(parent)
        loadUi('ui/merchant.ui', self)

        # Models and Tables Setup
        self.sourceModel = QStandardItemModel()
        self.destinationModel = QStandardItemModel()
        self.merchant_table.setModel(self.sourceModel)
        self.basket.setModel(self.destinationModel)

        # User and State
        self.username = UserSystem()
        self.current_username = current_username

        # Table Configuration
        self.merchant_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.merchant_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.basket.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        # Basket Header Setup
        self.destinationModel.setHorizontalHeaderLabels([
            'სახელი', 'რაოდ.', 'ფასი', 'ერთეული', 'სულ'
        ])
        self.basket.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.basket.horizontalHeader().resizeSection(0, 130)
        self.basket.horizontalHeader().resizeSection(1, 70)
        self.basket.horizontalHeader().resizeSection(2, 55)
        self.basket.horizontalHeader().resizeSection(3, 80)
        self.basket.horizontalHeader().resizeSection(4, 60)
        # Connect the click event to our update function
        self.merchant_table.clicked.connect(self.update_tax_display)
        # Signals and Event Filters
        self.filter_name.textChanged.connect(self.filter_item_with_name)
        self.merchant_table.doubleClicked.connect(self.paste_selected_row)
        self.merchant_table.installEventFilter(self)
        self.destinationModel.dataChanged.connect(self.handle_basket_data_change)
        self.basket.installEventFilter(self)

        # Button Connections
        self.checkout_button.clicked.connect(self.checkout)
        self.delete_button.clicked.connect(self.delete_product)
        self.return_2.clicked.connect(self.show_return_table)
        self.info_button.clicked.connect(self.show_info_window)
        self.generic_window.clicked.connect(self.show_generic_products)

        # Logging
        logging.basicConfig(
            filename='checkout.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # QSS/Styling
        self.load_qss('ui/Adaptic.qss')

        # Filter Checkboxes Setup
        self.quantity.blockSignals(True)
        self.date.blockSignals(True)
        self.quantity.setChecked(False)
        self.date.setChecked(False)
        self.quantity.blockSignals(False)
        self.date.blockSignals(False)

        # Using lambda to ignore signal argument
        self.quantity.stateChanged.connect(lambda: self.update_selectability())
        self.date.stateChanged.connect(lambda: self.update_selectability())

        # Initial Data Load
        self.load_data()

    # ====================================================================
    #           HELPER METHODS
    # ====================================================================

    def load_qss(self, file_path):
        qss_file = QFile(file_path)
        if qss_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
            style_sheet = QTextStream(qss_file).readAll()
            self.setStyleSheet(style_sheet)
        else:
            logging.warning(f"Failed to load QSS file: {file_path}")

    def update_tax_display(self, index):
        # 'index' tells us exactly which row was clicked
        row_idx = index.row()

        # 1. Get the data from the sourceModel (Merchant Table)
        # Price is at Index 2, Tax Info is at Index 4
        try:

            price_text = self.sourceModel.item(row_idx, 2).text()
            bruto_price = float(price_text)

        except (ValueError, AttributeError):
            bruto_price = 0.0
        item_nast = self.sourceModel.item(row_idx, 1).text()
        att_mat_info = self.sourceModel.item(row_idx, 4).text()
        # 2. Tax Calculation Logic
        is_taxable = "დღგ: იბეგრება" in att_mat_info

        # if is_taxable:
        #     # Calculate 18% tax from the selling price
        #     # If price is 0.27, tax is roughly 0.04
        #     tax_amount = base_price - (base_price / 1.18)
        #     self.tax1.setText(f" ნაშთი: {item_nast} | დღგ: იბეგრება | თანხა: {tax_amount:.3f}")
        #
        #     # Optional: Change style to show it's taxable (e.g., Red text)
        #     self.tax1.setStyleSheet("color: red; font-weight: bold;")
        # else:
        #     self.tax1.setText(f" ნაშთი: {item_nast} | დღგ: არ იბეგრება | თანხა: 0.000")
        #     self.tax1.setStyleSheet("color: green;")
        if is_taxable:
            # Calculate the breakdown
            net_price = bruto_price / 1.18
            tax_amount = bruto_price - net_price

            # Display: Net + Tax = Brutto
            # Example: 0.229 + 0.041 = 0.270 GEL
            display_text = (
                f"ნაშთი: {item_nast} | "
                f"{net_price:.3f} (ფასი) + {tax_amount:.3f} (დღგ) = {bruto_price:.2f} GEL"
            )
            self.tax1.setText(display_text)
            self.tax1.setStyleSheet("color: red; font-weight: bold; border: 1px solid red; background-color: #fff5f5;")
        else:
            # If not taxable, Net is the same as Brutto
            self.tax1.setText(f"ნაშთი: {item_nast} | ფასი: {bruto_price:.2f} GEL (დღგ-ს გარეშე)")
            self.tax1.setStyleSheet(
                "color: green; font-weight: bold; border: 1px solid green; background-color: #f5fff5;")

    def update_grand_total(self):
        total = 0.0
        for row in range(self.destinationModel.rowCount()):
            try:
                total_item = self.destinationModel.item(row, 4)
                if total_item and total_item.text():
                    total += float(total_item.text())
            except (ValueError, AttributeError):
                continue
        self.total_amount.setText(f"{total:.2f}")

    def update_total_tax_display(self):
        """Recalculates the total tax based on current basket quantities."""
        total_tax = 0.0
        for row in range(self.destinationModel.rowCount()):
            try:
                qty_item = self.destinationModel.item(row, 1)
                qty = float(qty_item.text()) if qty_item else 0.0

                price_item = self.destinationModel.item(row, 2)
                # Retrieve Unit Tax stored in UserRole + 4
                unit_tax = price_item.data(Qt.ItemDataRole.UserRole + 4)

                if unit_tax is None:
                    unit_tax = 0.0

                total_tax += qty * float(unit_tax)

            except (ValueError, AttributeError):
                continue

        self.tax.setText(f"{total_tax:.2f}")

    def calculate_tax_price(self, price: float, att_mat_info: str) -> float:
        if "დღგ: იბეგრება" in att_mat_info:
            taxed_price = price * (1 + VAT_RATE)
            return round(taxed_price, 2)
        else:
            return round(price, 2)

    def get_source_data_by_name(self, product_name: str) -> Dict[str, Union[float, str]]:
        model = self.sourceModel
        for row in range(model.rowCount()):
            name_item = model.item(row, 0)
            if name_item and name_item.text() == product_name:
                try:
                    brut_price = float(model.item(row, 2).text())
                    print(brut_price)
                except (ValueError, AttributeError):
                    brut_price = 0.0

                try:
                    zac_price = float(model.item(row, 6).text())
                    print(zac_price)
                except (ValueError, AttributeError):
                    zac_price = 0.0

                # try:
                #     cost_price = float(model.item(row, 2).text())
                # except (ValueError, AttributeError):
                #     cost_price = 0.0

                return {
                    'brut_price': brut_price,
                    'zac_price': zac_price,
                    'cost_price': zac_price,
                    'att_mat_info': model.item(row, 4).text()
                }
        return {'brut_price': 0.0, 'cost_price': 0.0, 'att_mat_info': ''}

    def selected_product_info(self) -> Union[str, None]:
        selected = self.basket.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Warning", "გთხოვთ, აირჩიეთ პროდუქტი კალათიდან ინფორმაციის სანახავად.")
            return None
        row = selected[0].row()
        product_name_item = self.destinationModel.item(row, 0)
        return product_name_item.text() if product_name_item else None

    # ====================================================================
    #           DATA LOADING AND DISPLAY METHODS
    # ====================================================================

    def load_data(self):
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                    SELECT
                        m."NAM_MAT",          -- 0
                        n."NAST",             -- 1
                        n."PRICE",            -- 2
                        n."DAT_GOOD",         -- 3
                        m."ATT_MAT",          -- 4
                        n."SER_NUM",          -- 5
                        n."ZAK_PRI",          -- 6
                        m."COD_MAT",          -- 7
                        n."COD_MAT"           -- 8
                    FROM
                        public.mater1 AS m
                    JOIN
                        public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
                    """)
                    raw_data = cursor.fetchall()

                    processed_data = []
                    for row_data in raw_data:
                        att_mat_string = row_data[4]
                        translated_field = ""

                        if att_mat_string and len(att_mat_string) >= 13:
                            vat_code = att_mat_string[6]
                            recipe_code = att_mat_string[12]
                            vat_display = 'იბეგრება' if vat_code == '1' else 'არ იბეგრება'
                            recipe_display = 'რეცეპტით' if recipe_code == '1' else 'ურეცეპტო'
                            translated_field = f"დღგ: {vat_display} / {recipe_display}"

                        new_row = [
                            row_data[0], row_data[1], row_data[2], row_data[3],
                            translated_field, row_data[5], row_data[6], row_data[7],
                            row_data[8]
                        ]
                        processed_data.append(tuple(new_row))

                    self.display_source_data(processed_data, ['dummy'] * 7)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")


    def display_source_data(self, data: List[tuple], column_headers: List[str]):
        self.sourceModel.clear()
        source_georgian_headers = [
            'სახელი', 'ნაშთი', 'ფასი', 'ვადა', 'დღ/სპ', 'სერიული ნომერი', 'ფასი(შიდა)', 'cod_mat(mater)', 'cod_mat(nast)'
        ]
        self.sourceModel.setHorizontalHeaderLabels(source_georgian_headers)

        self.merchant_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.merchant_table.horizontalHeader().resizeSection(0, 250)
        self.merchant_table.horizontalHeader().resizeSection(1, 110)
        self.merchant_table.horizontalHeader().resizeSection(2, 90)
        self.merchant_table.horizontalHeader().resizeSection(3, 100)
        self.merchant_table.horizontalHeader().resizeSection(4, 220)
        self.merchant_table.horizontalHeader().resizeSection(5, 150)
        self.merchant_table.horizontalHeader().resizeSection(6, 110)
        self.merchant_table.horizontalHeader().resizeSection(7, 110)
        self.merchant_table.horizontalHeader().resizeSection(8, 110)

        today = datetime.date.today()

        if data:
            self.sourceModel.beginInsertRows(QModelIndex(), 0, len(data) - 1)
            for row_data in data:
                is_available = True
                is_not_out_of_date = True
                disable_reason = ""

                try:
                    current_stock = float(row_data[1])
                    if current_stock <= 0.0:
                        is_available = False
                        disable_reason = "ნაშთი ამოწურულია"
                except (ValueError, IndexError, TypeError):
                    is_available = False
                    disable_reason = "ნაშთის მონაცემი არასწორია"

                if is_not_out_of_date:
                    date_str = str(row_data[3]).strip()
                    if date_str and date_str.lower() not in ['none', 'null']:
                        try:
                            expiration_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                            if expiration_date < today:
                                is_not_out_of_date = False
                                disable_reason = "ვადაგასულია"
                        except ValueError:
                            is_not_out_of_date = False
                            disable_reason = "თარიღის ფორმატი არასწორია"

                row_items = [QStandardItem(str(cell_data)) for cell_data in row_data]

                for i, item in enumerate(row_items):
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

                    if not is_available or not is_not_out_of_date:
                        if i == 0:
                            from PyQt6.QtGui import QBrush, QColor
                            item.setForeground(QBrush(QColor('red')))
                            item.setToolTip(f"⚠️ გაფრთხილება: {row_data[i]} - {disable_reason}.")

                    if i == 0:
                        item.setToolTip(item.toolTip() or f"პროდუქტის დასახელება: {row_data[i]}")

                self.sourceModel.appendRow(row_items)
            self.sourceModel.endInsertRows()

    # ====================================================================
    #           FILTERING AND SELECTION LOGIC
    # ====================================================================

    def filter_item_with_name(self):
        filter_text = self.filter_name.text().lower()
        model = self.sourceModel

        for row in range(model.rowCount()):
            name_item = model.item(row, 0)
            is_match = name_item and filter_text in name_item.text().lower()
            self.merchant_table.setRowHidden(row, not is_match)

        self.update_selectability(after_name_filter=True)

    def update_selectability(self, after_name_filter=False):
        is_quantity_filter_active = self.quantity.isChecked()
        is_date_filter_active = self.date.isChecked()

        if not is_quantity_filter_active and not is_date_filter_active:
            if after_name_filter: return
            self.filter_item_with_name()
            return

        today = datetime.date.today()
        model = self.sourceModel

        for row in range(model.rowCount()):
            if after_name_filter and self.merchant_table.isRowHidden(row):
                continue

            should_be_hidden = False
            stock_item = model.item(row, 1)
            date_item = model.item(row, 3)

            if is_quantity_filter_active:
                try:
                    current_stock = float(stock_item.text())
                    if current_stock <= 0.0: should_be_hidden = True
                except (ValueError, AttributeError, TypeError):
                    should_be_hidden = True

            if not should_be_hidden and is_date_filter_active:
                date_str = date_item.text().strip()
                if date_str and date_str.lower() not in ['none', 'null']:
                    try:
                        expiration_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        if expiration_date < today: should_be_hidden = True
                    except ValueError:
                        should_be_hidden = True
                else:
                    should_be_hidden = True

            self.merchant_table.setRowHidden(row, should_be_hidden)

        self.merchant_table.viewport().repaint()

    # ====================================================================
    #           BASKET MANIPULATION
    # ====================================================================

    def paste_selected_row(self):
        selected_indexes = self.merchant_table.selectionModel().selectedRows()
        if not selected_indexes: return

        selected_row_index_from_source = selected_indexes[0].row()

        product_name_item = self.sourceModel.item(selected_row_index_from_source, 0)
        price_item = self.sourceModel.item(selected_row_index_from_source, 2)
        product_dat = self.sourceModel.item(selected_row_index_from_source, 3).text()
        product_nast = self.sourceModel.item(selected_row_index_from_source, 1).text()
        date_now = datetime.date.today()

        try:
            if float(product_nast) == 0.0:
                QMessageBox.information(self, 'Out of stock', 'პროდუქტი არ არის მარაგში.')
                return
            if product_dat.strip().lower() in ['', 'none', 'null']:
                QMessageBox.information(self, 'Product expired', 'პროდუქტი ვადაგასულია (ვადა არ არის მითითებული).')
                return
            expiration_date_from_db = datetime.datetime.strptime(product_dat, '%Y-%m-%d').date()
            if expiration_date_from_db < date_now:
                QMessageBox.information(self, 'Product expired', 'პროდუქტი ვადაგასულია.')
                return
        except ValueError as e:
            QMessageBox.warning(self, 'Error', f'Failed to process product data. Details: {e}')
            return

        product_name_full = product_name_item.text() if product_name_item else ""
        price_str = price_item.text() if price_item else "0.0"
        att_mat_info_item = self.sourceModel.item(selected_row_index_from_source, 4)
        att_mat_info = att_mat_info_item.text() if att_mat_info_item else ""

        try:
            base_price = float(price_str)
        except ValueError:
            base_price = 0.0

        quantity_in_basket_initial = 0
        final_price = self.calculate_tax_price(base_price, att_mat_info)

        is_taxable = "დღგ: იბეგრება" in att_mat_info
        if is_taxable and (1 + VAT_RATE) != 0:
            net_price = final_price / (1 + VAT_RATE)
            tax_amount_unit = final_price - net_price
            # self.tax1.setText(f'იბეგრება{tax_amount_unit:.2f} GEL')
        else:
            tax_amount_unit = 0.0
            # self.tax1.setText(f'არ იბეგრება')

        product_unit_quantity_parsed_from_name = 0
        pattern = r'#(\d+)(?:ტ|ა|დრ)'
        match = re.search(pattern, product_name_full)
        if match:
            try:
                product_unit_quantity_parsed_from_name = int(match.group(1))
            except ValueError:
                product_unit_quantity_parsed_from_name = 0

        initial_total = quantity_in_basket_initial * final_price

        new_row_items = [
            QStandardItem(product_name_full),
            QStandardItem(str(quantity_in_basket_initial)),
            QStandardItem(f"{final_price:.2f}"),
            QStandardItem('0'),
            QStandardItem(f"{initial_total:.2f}")
        ]

        new_row_items[0].setToolTip(f"პროდუქტი: {product_name_full}\nფასი: {final_price:.2f}")
        new_row_items[3].setData(product_unit_quantity_parsed_from_name, Qt.ItemDataRole.UserRole + 3)
        new_row_items[2].setData(tax_amount_unit, Qt.ItemDataRole.UserRole + 4)

        new_row_items[0].setFlags(new_row_items[0].flags() & ~Qt.ItemFlag.ItemIsEditable)
        new_row_items[4].setFlags(new_row_items[4].flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.destinationModel.appendRow(new_row_items)
        self.update_grand_total()
        self.update_total_tax_display()

    def handle_basket_addition(self, product_data: list):
        product_name_full = product_data[0]
        price_str = product_data[1]
        att_mat_info = attmat.translate_attributes(product_data[2])

        try:
            base_price = float(price_str)
        except ValueError:
            base_price = 0.0

        final_price = self.calculate_tax_price(base_price, att_mat_info)

        is_taxable = "დღგ: იბეგრება" in att_mat_info
        if is_taxable and (1 + VAT_RATE) != 0:
            net_price = final_price / (1 + VAT_RATE)
            tax_amount_unit = final_price - net_price
        else:
            tax_amount_unit = 0.0

        product_unit_quantity_parsed_from_name = 0
        pattern = r'#(\d+)(?:ტ|ა|დრ)'
        match = re.search(pattern, product_name_full)
        if match:
            try:
                product_unit_quantity_parsed_from_name = int(match.group(1))
            except ValueError:
                product_unit_quantity_parsed_from_name = 0

        quantity_in_basket_initial = 0
        initial_total = quantity_in_basket_initial * final_price

        new_row_items = [
            QStandardItem(product_name_full),
            QStandardItem(str(quantity_in_basket_initial)),
            QStandardItem(f"{final_price:.2f}"),
            QStandardItem('0'),
            QStandardItem(f"{initial_total:.2f}")
        ]

        new_row_items[0].setToolTip(f"პროდუქტი: {product_name_full}\nფასი: {final_price:.2f}")
        new_row_items[3].setData(product_unit_quantity_parsed_from_name, Qt.ItemDataRole.UserRole + 3)
        new_row_items[2].setData(tax_amount_unit, Qt.ItemDataRole.UserRole + 4)

        new_row_items[0].setFlags(new_row_items[0].flags() & ~Qt.ItemFlag.ItemIsEditable)
        new_row_items[4].setFlags(new_row_items[4].flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.destinationModel.appendRow(new_row_items)
        self.update_grand_total()
        self.update_total_tax_display()

        logging.info(f"Product added: {product_name_full}")
        QMessageBox.information(self, "Basket Update", f"✅ პროდუქტი '{product_name_full}' დაემატა კალათაში.")

    def handle_basket_data_change(self, top_left_index: QModelIndex, bottom_right_index: QModelIndex):
        changed_row = top_left_index.row()
        changed_col = top_left_index.column()

        if changed_col in [1, 2, 3]:
            try:
                qty_item = self.destinationModel.item(changed_row, 1)
                price_item = self.destinationModel.item(changed_row, 2)
                unit_qty_item = self.destinationModel.item(changed_row, 3)

                qty = float(qty_item.text()) if qty_item and qty_item.text() else 0.0
                price = float(price_item.text()) if price_item and price_item.text() else 0.0
                current_unit_qty = float(unit_qty_item.text()) if unit_qty_item and unit_qty_item.text() else 0.0

                # Retrieve original internal units
                original_internal_units = unit_qty_item.data(Qt.ItemDataRole.UserRole + 3) or 0

                new_total = 0.0

                if changed_col == 3:  # Unit Qty Changed
                    if original_internal_units > 0:
                        new_qty = current_unit_qty / original_internal_units
                        # Update main quantity without triggering infinite loop if possible
                        # (Signals are naturally handled, but ensure logic holds)
                        self.destinationModel.blockSignals(True)
                        qty_item.setText(f"{new_qty:.2f}")
                        self.destinationModel.blockSignals(False)
                        new_total = (price / original_internal_units) * current_unit_qty
                        qty = new_qty
                    else:
                        new_total = qty * price

                elif changed_col == 1:  # Main Qty Changed
                    if original_internal_units > 0:
                        new_unit_qty = qty * original_internal_units
                        self.destinationModel.blockSignals(True)
                        unit_qty_item.setText(str(new_unit_qty))
                        self.destinationModel.blockSignals(False)
                    new_total = qty * price

                else:  # Price Changed
                    new_total = qty * price

                # Update Total Column
                self.destinationModel.blockSignals(True)
                self.destinationModel.item(changed_row, 4).setText(f"{new_total:.2f}")
                self.destinationModel.blockSignals(False)

                self.update_grand_total()
                self.update_total_tax_display()

            except ValueError:
                pass

    def delete_product(self):
        selected_indexes = self.basket.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "Warning", "გთხოვთ, აირჩიეთ წასაშლელი პროდუქტი.")
            return
        row = selected_indexes[0].row()
        self.destinationModel.removeRow(row)
        self.update_grand_total()
        self.update_total_tax_display()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if obj == self.merchant_table:
                if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                    self.paste_selected_row()
                    return True
            elif obj == self.basket:
                if event.key() == Qt.Key.Key_Delete:
                    self.delete_product()
                    return True
        return super().eventFilter(obj, event)

    def show_generic_products(self):
        selected = self.merchant_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Warning", "გთხოვთ, აირჩიეთ პროდუქტი ცხრილიდან.")
            return
        row = selected[0].row()
        product_name_item = self.sourceModel.item(row, 0)
        if product_name_item is None: return
        selected_name = product_name_item.text()
        self.generic_dialog = CodeGeneric(selected_name, parent=self)
        self.generic_dialog.product_selected_for_basket.connect(self.handle_basket_addition)
        self.generic_dialog.exec()

    def show_return_table(self):
        self.return_table = ReturnProduct()
        self.return_table.product_returned.connect(self.load_data)
        self.return_table.showMaximized()

    def show_info_window(self):
        product_name = self.selected_product_info()
        if not product_name: return
        raw_att_mat_string = attmat.get_material_attribute(product_name)
        if raw_att_mat_string:
            translated_attributes = attmat.translate_attributes(raw_att_mat_string)
            dialog = InfoDialog(translated_attributes=translated_attributes, material_name=product_name, parent=self)
            dialog.exec()
        else:
            QMessageBox.information(self, "ინფორმაცია", f"პროდუქტისთვის '{product_name}' ვერ მოიძებნა ატრიბუტები.")

    # --- CHECKOUT METHOD ---
    def checkout(self):
        try:
            total_price = float(self.total_amount.text())
        except ValueError:
            total_price = 0.0

        if self.destinationModel.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "კალათა ცარიელია. დაამატეთ პროდუქტი.")
            return

        operations_data_list = []
        context_list = []

        for row in range(self.destinationModel.rowCount()):
            try:
                product_name = self.destinationModel.item(row, 0).text()
                customer_qty = float(self.destinationModel.item(row, 1).text())
                final_price_unit = float(self.destinationModel.item(row, 2).text())
                unit_quantity = self.destinationModel.item(row, 3).data(Qt.ItemDataRole.UserRole + 3)
                if unit_quantity is None or unit_quantity == 0:
                    unit_quantity = float(self.destinationModel.item(row, 3).text())

            except Exception:
                return

            source_info = self.get_source_data_by_name(product_name)

            # 1. Capture the REAL cost from the 'nast' table (0.432)
            # source_info['cost_price'] comes from Index 6 (ZAK_PRI)
            real_purchase_cost = source_info.get('zac_price', 0.0)

            att_mat_info = source_info.get('att_mat_info', '')
            is_taxable = "დღგ: იბეგრება" in att_mat_info

            # 2. Tax Logic (Calculates net selling price, NOT the cost)
            if is_taxable:
                # If final_price_unit is 0.27, net_price_unit becomes 0.23
                net_price_unit = final_price_unit / 1.18
                tax_unit = final_price_unit - net_price_unit
            else:
                net_price_unit = final_price_unit
                tax_unit = 0.0

            # 3. Profit Calculation
            # danamati_sul = (0.27 - 0.432) * quantity
            total_selling_price = final_price_unit * customer_qty
            total_cost_price = real_purchase_cost * customer_qty
            danamati_sul = total_selling_price - total_cost_price
            danamati_percent = (danamati_sul / total_cost_price * 100) if total_cost_price > 0 else 0.0

            # 4. Prepare for Database
            operations_data_list.append({
                'product_name': product_name,
                'customer_qty': customer_qty,
                'unit_quantity': unit_quantity,
                'final_price': final_price_unit,
                'brut_price': final_price_unit,
                'net_price': net_price_unit,  # This is 0.23
                'tax_unit': tax_unit,
                'sh_price': final_price_unit,  # This is 0.27
                'zac_price': real_purchase_cost,  # THIS WILL NOW BE 0.432
                'danamati_sul': danamati_sul,
                'danamati_percent': danamati_percent,
                'tax_payed': tax_unit * customer_qty,
                'tx_not_payed': 0.0,
                'sold': False
            })

            # source_info = self.get_source_data_by_name(product_name)
            # brut_price_unit = source_info.get('brut_price', 0.0)
            # zac_price_unit = source_info.get('cost_price', 0.0)
            # cost_unit = source_info.get('cost_price', 0.0)
            # att_mat_info = source_info.get('att_mat_info', '')
            # is_taxable = "დღგ: იბეგრება" in att_mat_info
            # if is_taxable:
            #     # final_price_unit is the Brutto (9.32)
            #     brut_price_unit = final_price_unit
            #     # Extract the Net price (7.90)
            #     net_price_unit = brut_price_unit / 1.18
            #     # The difference is the tax (1.42)
            #     tax_unit = brut_price_unit - net_price_unit
            # else:
            #     net_price_unit = final_price_unit
            #     brut_price_unit = net_price_unit
            #     tax_unit = 0.0
            #
            #
            # total_selling_price = final_price_unit * customer_qty
            # total_cost_price = cost_unit * customer_qty
            # danamati_sul = cost_unit - zac_price_unit
            # danamati_percent = (danamati_sul / total_cost_price) * 100 if total_cost_price > 0 else 0.0
            # tax_payed = float(tax_unit * customer_qty)
            # tx_not_payed = 0.0
            #
            context_list.append({
                'პროდუქტის სახელი': product_name, 'რაოდენობა': str(customer_qty),
                'ერთეულის რაოდენობა': str(unit_quantity), 'ფასი': f"{final_price_unit:.2f}"
            })
            #
            # operations_data_list.append({
            #     'product_name': product_name, 'customer_qty': customer_qty,
            #     'unit_quantity': unit_quantity, 'final_price': final_price_unit,
            #     'brut_price': brut_price_unit, 'net_price': net_price_unit,
            #     'tax_unit': tax_unit, 'sh_price': final_price_unit, 'zac_price': cost_unit,
            #     'danamati_sul': danamati_sul, 'danamati_percent': danamati_percent,
            #     'tax_payed': tax_payed, 'tx_not_payed': tx_not_payed,
            #     'sold': False
            # })
        source_info = self.get_source_data_by_name(product_name)
        print(f"DEBUG: Product: {product_name} | Cost from Helper: {source_info.get('zac_price')}")
        invoice_number = random.randint(100000, 999999)
        created_date = datetime.date.today().strftime('%Y-%m-%d')
        created_time = datetime.datetime.now().strftime('%H:%M:%S')

        invoice_context = {
            'invoice_number': invoice_number, 'created_date': f'{created_date} / {created_time}',
            'items': context_list, 'total_price': f"{total_price:.2f}"
        }

        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO invoices (invoice_id, username, total_price, created_at) 
                        VALUES (%s, %s, %s, %s)
                        """,
                        (invoice_number, self.current_username, total_price, f'{created_date}/{created_time}')
                    )
                    # 2. Insert each product into the 'operations' table
                    for item in operations_data_list:
                        cursor.execute(
                            """
                            INSERT INTO operations (
                                invoice_id,        -- 1
                                product_name,      -- 2
                                quantity,          -- 3
                                item_quantity,     -- 4
                                price,             -- 5
                                date,              -- 6
                                brut_price,        -- 7
                                net_price,         -- 8
                                tax,               -- 9
                                sh_price,          -- 10 (Sales Price: e.g. 0.62)
                                zac_price,         -- 11 (Internal Cost: e.g. 0.432)
                                danamati_sul,      -- 12
                                danamati_percent,  -- 13
                                tax_payed,         -- 14
                                tax_not_payed,     -- 15
                                sold               -- 16
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                invoice_number,  # 1
                                item['product_name'],  # 2
                                item['customer_qty'],  # 3
                                item['unit_quantity'],  # 4
                                item['final_price'],  # 5
                                f'{created_date}/{created_time}',  # 6
                                item['brut_price'],  # 7
                                item['net_price'],  # 8
                                item['tax_unit'],  # 9
                                item['sh_price'],  # 10 maps to sh_price
                                item['zac_price'],  # 11 maps to zac_price (The 0.432)
                                item['danamati_sul'],  # 12
                                item['danamati_percent'],  # 13
                                item['tax_payed'],  # 14
                                item['tx_not_payed'],  # 15
                                item['sold']  # 16
                            )
                        )
                    # for item_data in operations_data_list:
                    #     cursor.execute(
                    #         """
                    #         INSERT INTO operations (
                    #             invoice_id, product_name, quantity, item_quantity, price, date,
                    #             brut_price, net_price, tax, sh_price, zac_price,
                    #             danamati_sul, danamati_percent, tax_payed, tax_not_payed, sold
                    #         ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    #         """,
                    #         (
                    #             invoice_number, item_data['product_name'], item_data['customer_qty'],
                    #             item_data['unit_quantity'], item_data['final_price'], f'{created_date}/{created_time}',
                    #             item_data['brut_price'], item_data['net_price'], item_data['tax_unit'],
                    #             item_data['sh_price'], item_data['zac_price'], item_data['danamati_sul'],
                    #             item_data['danamati_percent'], item_data['tax_payed'], item_data['tx_not_payed'],
                    #             item_data['sold']
                    #         )
                    #     )
                    conn.commit()
                    self.load_data()

                    if self.quantity.isChecked() or self.date.isChecked():
                        self.update_selectability()

        except Exception as db_insert_e:
            QMessageBox.critical(self, "Database Error", f"Error: {db_insert_e}")
            return

        folder_name = "invoices"
        target_folder = pathlib.Path(folder_name)
        target_folder.mkdir(parents=True, exist_ok=True)
        filename = f'Invoice({created_date})#{invoice_number}.pdf'
        full_path = os.path.join('invoices', filename)

        invoice_creation = QMessageBox.question(self, 'ქვითრის შექმნა', 'შევქმნათ ქვითარი?',
                                                QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
        if invoice_creation == QMessageBox.StandardButton.Yes:
            try:
                template_loader = jinja2.FileSystemLoader('./')
                template_env = jinja2.Environment(loader=template_loader)
                template = template_env.get_template('invoice.html')
                output_text = template.render(invoice_context)
                config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
                pdfkit.from_string(output_text, full_path, configuration=config)
            except Exception as e:
                QMessageBox.warning(self, 'Invoice creation Error', f'ქვითრის შექმნა ვერ მოხერხდა: {e}')

        database_changes = QMessageBox.question(self, 'მონაცემთა ბაზაში ცვლილებების შეტანა',
                                                'შევიტანო ბაზაში ცვლილებები?',
                                                QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
        if database_changes == QMessageBox.StandardButton.Yes:
            try:
                with db.connect() as conn:
                    with conn.cursor() as cursor:
                        for item in context_list:
                            product_name = item['პროდუქტის სახელი']
                            quantity_sold = item['რაოდენობა']
                            cursor.execute(
                                "SELECT \"COD_MAT\" FROM public.mater1 WHERE \"NAM_MAT\" = %s",
                                (product_name,)
                            )
                            cod_mat = cursor.fetchone()
                            if cod_mat:
                                cursor.execute(
                                    """
                                    UPDATE public.nashti 
                                    SET "NAST" = "NAST" - %s 
                                    WHERE "COD_MAT" = %s
                                    """,
                                    (quantity_sold, cod_mat[0])
                                )
                        cursor.execute(
                            """
                            UPDATE operations 
                            SET sold = TRUE 
                            WHERE invoice_id = %s
                            """,
                            (invoice_number,)
                        )

                        conn.commit()
                        self.load_data()

                if self.quantity.isChecked() or self.date.isChecked():
                    self.update_selectability()

                QMessageBox.information(self, "Success", "მონაცემები წარმატებით განახლდა!")
            except Exception as db_e:
                QMessageBox.critical(self, "Database Error", f"Error: {db_e}")

        logging.info(f"Checkout successful. Username: {self.current_username} . Invoice created: {full_path}")

        if os.path.exists(full_path):
            reply = QMessageBox.question(self, 'ინვოისის ამობეჭდვა', 'ინვოისი წარმატებით შეიქმნა!, გსურთ ამობეჭდვა?',
                                         QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.startfile(full_path)
                except Exception as e:
                    QMessageBox.critical(self, "Print Error", f"ინვოისის გახსნა ვერ მოხერხდა: {e}")

        self.destinationModel.setRowCount(0)
        self.total_amount.clear()
        self.tax.setText("0.00")