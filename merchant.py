from PyQt6.QtCore import QModelIndex, QFile, QIODevice, QTextStream, Qt, QEvent
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (QWidget, QMessageBox, QLineEdit, QComboBox,
                             QTextEdit, QTableWidget, QCheckBox, QTableView, QHeaderView, QApplication)
from PyQt6.uic import loadUi
import random
import psycopg2
import datetime
import os
import pathlib
from user_system import UserSystem
from typing import List, Union, Dict, Any
import logging
import jinja2
import pdfkit
import re
from return_function import ReturnProduct
from user_system import UserSystem
from database import Database
from att_mat import MaterialAttributeTranslator
db = Database()
attmat = MaterialAttributeTranslator()
from info_dialog import InfoDialog
from generic import CodeGeneric


class MerchantTable(QWidget):
    def __init__(self, parent=None, current_username=''):
        super().__init__(parent)
        loadUi('ui/merchant.ui', self)
        self.sourceModel = QStandardItemModel()
        self.destinationModel = QStandardItemModel()
        self.merchant_table.setModel(self.sourceModel)
        self.filter_name.textChanged.connect(self.filter_item_with_name)
        self.merchant_table.setModel(self.sourceModel)
        self.basket.setModel(self.destinationModel)
        self.username = UserSystem()
        self.merchant_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.merchant_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        # self.merchant_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.merchant_table.resizeColumnsToContents()  # Often conflicts with Stretch, keep if specific columns are too wide/narrow
        # self.merchant_table.horizontalHeader().setStretchLastSection(True) # Only if you want last section to take all remaining space
        self.current_username = current_username
        # self.basket.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Ensure the basket table cells are editable by double-click
        # Default is usually QAbstractItemView.DoubleClicked or EditKeyPressed
        # If your cells are not editable, you might explicitly set:
        # self.basket.setEditTriggers(QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.AnyKeyPressed)

        self.merchant_table.doubleClicked.connect(self.paste_selected_row)
        self.merchant_table.installEventFilter(self)


        # --- Set the desired headers for the DESTINATION table (basket) ---
        self.destinationModel.setHorizontalHeaderLabels([
            'სახელი',  # Column 0: Display only
            'რაოდ.',  # Column 1: Editable (customer_qty)
            'ფასი',  # Column 2: Editable (product_unit_price)
            'ერთ. რაოდ.',  # Column 3: Editable (sold_internal_units)
            'სულ'  # Column 4: Calculated, not directly editable by user
        ])
        self.basket.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.basket.horizontalHeader().resizeSection(0, 212)
        self.basket.horizontalHeader().resizeSection(1, 70)
        self.basket.horizontalHeader().resizeSection(2, 55)
        self.basket.horizontalHeader().resizeSection(3, 110)
        self.basket.horizontalHeader().resizeSection(4, 60)

        # --- End of destination header setup ---

        # Connect the dataChanged signal of the destinationModel
        # This will now handle updates for changes in Quantity, Price, OR Unit Quantity
        self.destinationModel.dataChanged.connect(self.handle_basket_data_change)
        self.basket.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # --- Configure the logger ---
        logging.basicConfig(
            filename='checkout.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        # --- End of logger configuration ---
        self.load_qss('ui/Adaptic.qss')
        self.load_data()
        # self.basket.resizeColumnsToContents()
        self.checkout_button.clicked.connect(self.checkout)
        self.delete_button.clicked.connect(self.delete_product)
        self.basket.installEventFilter(self)
        self.return_2.clicked.connect(self.show_return_table)
        self.info_button.clicked.connect(self.show_info_window)
        self.generic_window.clicked.connect(self.show_generic_products)

    def show_generic_products(self):
        """
        Retrieves the selected product name from the main table,
        opens the CodeGeneric dialog, and connects its signal.
        """
        selected = self.merchant_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Warning", "გთხოვთ, აირჩიეთ პროდუქტი ცხრილიდან.")
            return

        row = selected[0].row()
        product_name_item = self.sourceModel.item(row, 0)

        if product_name_item is None:
            QMessageBox.critical(self, "Error", "პროდუქტის სახელის აღება ვერ მოხერხდა.")
            return

        selected_name = product_name_item.text()

        self.generic_dialog = CodeGeneric(selected_name, parent=self)

        # CRUCIAL STEP: Connect the signal from the dialog to this method
        self.generic_dialog.product_selected_for_basket.connect(self.handle_basket_addition)

        self.generic_dialog.exec()

    def show_return_table(self):
        self.return_table = ReturnProduct()
        # 2. Connect the new signal to the MerchantTable's load_data method
        # This ensures that when the ReturnProduct window successfully returns an item,
        # it automatically triggers a refresh of the main MerchantTable.
        self.return_table.product_returned.connect(self.load_data)
        self.return_table.showMaximized()

    def show_info_window(self):
        """
        Retrieves the selected product name from the Baskets table,
        translates its attributes using attmat, and displays the InfoDialog.
        """
        # --- NEW STEP: Get the product name using the helper method ---
        product_name = self.selected_product_info()

        if not product_name:
            # selected_product_info already showed a warning, so just exit
            return

        # 1. Use the MaterialAttributeTranslator to get the raw string
        # This will use the actual DB if connected, or the test string otherwise.
        raw_att_mat_string = attmat.get_material_attribute(product_name)

        if raw_att_mat_string:
            # 2. Translate the raw string into a descriptive list
            translated_attributes = attmat.translate_attributes(raw_att_mat_string)

            # 3. Create and show the dedicated dialog instance
            dialog = InfoDialog(
                translated_attributes=translated_attributes,
                material_name=product_name,
                parent=self
            )
            dialog.exec()
        else:
            QMessageBox.information(self, "ინფორმაცია", f"პროდუქტისთვის '{product_name}' ვერ მოიძებნა ატრიბუტები.")

    def handle_basket_addition(self, product_data: list):
        """
        RECEIVES the signal from CodeGeneric and adds the selected product
        to the basket (self.destinationModel).

        product_data indices from CodeGeneric:
        [Name(0), Price(1), ATT_MAT(2), DATE(3), Stock(4), Serial(5), COD_GEN(6)]
        """
        # 1. Extract necessary fields from the received product_data
        product_name_full = product_data[0]  # Full Name
        price_str = product_data[1]  # Price as string
        stock = product_data[4]  # Stock as string
        # serial_number = product_data[5]   # Serial Number (optional for display)

        # 2. Validation
        # try:
        #     if float(stock) <= 0:
        #         QMessageBox.warning(self, "Stock Warning", f"პროდუქტი '{product_name_full}' ნაშთში აღარ არის.")
        #         return
        #     price = float(price_str)
        # except ValueError:
        #     QMessageBox.critical(self, "Error", f"არასწორი ფასის მონაცემი: {price_str}")
        #     return

        # 3. Determine product unit quantity from name (Same logic as paste_selected_row)
        price = float(price_str)
        product_unit_quantity_parsed_from_name = 0
        pattern = r'#(\d+)(?:ტ|ა|დრ)'
        match = re.search(pattern, product_name_full)

        if match:
            try:
                product_unit_quantity_parsed_from_name = int(match.group(1))
            except ValueError:
                product_unit_quantity_parsed_from_name = 0

        # 4. Create and add new row to the basket model
        quantity_in_basket_initial = 0  # Default initial quantity is 1
        initial_total = quantity_in_basket_initial * price

        new_row_items = [
            QStandardItem(product_name_full),  # 0: სახელი (Name)
            QStandardItem(str(quantity_in_basket_initial)),  # 1: რაოდენობა (Qty)
            QStandardItem(f"{price:.2f}"),  # 2: ღირებულება (Price)
            QStandardItem(str(product_unit_quantity_parsed_from_name)),  # 3: ერთეულის რაოდენობა (Unit Qty)
            QStandardItem(f"{initial_total:.2f}")  # 4: სულ (Total)
        ]

        # Store the original parsed product_unit_quantity in the hidden role
        new_row_items[3].setData(product_unit_quantity_parsed_from_name, Qt.ItemDataRole.UserRole + 3)

        # Set read-only flags for specific columns
        new_row_items[0].setFlags(new_row_items[0].flags() & ~Qt.ItemFlag.ItemIsEditable)  # Product Name
        new_row_items[4].setFlags(new_row_items[4].flags() & ~Qt.ItemFlag.ItemIsEditable)  # Total

        self.destinationModel.appendRow(new_row_items)
        self.update_grand_total()

        logging.info(f"Product added from Generic: {product_name_full}, Price: {price}, Qty: 1")
        # Optional: Provide UI feedback
        QMessageBox.information(self, "Basket Update", f"✅ პროდუქტი '{product_name_full}' დაემატა კალათაში.")

    # ----------------------------------------------------------------------
    # --- EXISTING METHODS (Modified/Placeholder) ---
    # ----------------------------------------------------------------------

    # ... (Your existing methods remain here, including:
    #      show_return_table, show_info_window, _apply_filter, filter_item_

    def _apply_filter(self, filter_text, column):
        """Helper method to apply filtering to a specific column"""
        for row in range(self.sourceModel.rowCount()):
            item = self.sourceModel.item(row, column)
            match = item is not None and filter_text in item.text().lower()
            self.merchant_table.setRowHidden(row, not match)

    def filter_item_with_name(self):
        filter_text = self.filter_name.text().lower()
        self._apply_filter(filter_text, column=0)

    def handle_basket_data_change(self, top_left_index: QModelIndex, bottom_right_index: QModelIndex):
        changed_row = top_left_index.row()
        changed_col = top_left_index.column()

        # Define column indices for clarity
        customer_qty_col_idx = 1
        product_unit_price_col_idx = 2
        sold_internal_units_col_idx = 3
        total_col_idx = 4

        # The calculation should happen if a quantity or price column is changed
        if changed_col in [customer_qty_col_idx, product_unit_price_col_idx, sold_internal_units_col_idx]:
            try:
                # Get data from the row
                customer_qty_item = self.destinationModel.item(changed_row, customer_qty_col_idx)
                sold_internal_units_item = self.destinationModel.item(changed_row, sold_internal_units_col_idx)
                price_item = self.destinationModel.item(changed_row, product_unit_price_col_idx)

                # Use '0' as default for empty cells
                customer_qty_str = customer_qty_item.text() if customer_qty_item else "0"
                sold_internal_units_str = sold_internal_units_item.text() if sold_internal_units_item else "0"
                price_str = price_item.text() if price_item else "0.0"

                customer_qty = float(customer_qty_str)
                sold_internal_units = float(sold_internal_units_str)
                product_unit_price = float(price_str)

                # Get the original parsed product_unit_quantity from the UserRole
                original_parsed_product_total_internal_units = sold_internal_units_item.data(
                    Qt.ItemDataRole.UserRole + 3) or 0

                new_total = 0.0

                # --- DYNAMIC CALCULATION LOGIC ---
                if changed_col == sold_internal_units_col_idx:
                    # Scenario 1: User changed 'ერთეულის რაოდენობა' (sold_internal_units)
                    if original_parsed_product_total_internal_units > 0:
                        # Calculate new 'რაოდენობა' (customer_qty) and round it
                        calculated_customer_qty = sold_internal_units / original_parsed_product_total_internal_units
                        self.destinationModel.setData(
                            self.destinationModel.index(changed_row, customer_qty_col_idx),
                            f"{calculated_customer_qty:.2f}",
                            Qt.ItemDataRole.DisplayRole
                        )
                        # Calculate the new total based on internal units
                        new_total = (
                                                product_unit_price / original_parsed_product_total_internal_units) * sold_internal_units
                    else:
                        # If original units are 0, just use the entered values
                        new_total = customer_qty * product_unit_price

                elif changed_col == customer_qty_col_idx:
                    # Scenario 2: User changed 'რაოდენობა' (customer_qty)
                    # Update 'ერთეულის რაოდენობა' (sold_internal_units)
                    calculated_sold_units = customer_qty * original_parsed_product_total_internal_units
                    self.destinationModel.setData(
                        self.destinationModel.index(changed_row, sold_internal_units_col_idx),
                        str(calculated_sold_units),
                        Qt.ItemDataRole.DisplayRole
                    )
                    # Standard total price calculation
                    new_total = customer_qty * product_unit_price

                else:
                    # Scenario 3: User changed the price, or some other case
                    new_total = customer_qty * product_unit_price

                # Update the 'სულ' (Total) column
                self.destinationModel.setData(
                    self.destinationModel.index(changed_row, total_col_idx),
                    f"{new_total:.2f}",
                    Qt.ItemDataRole.DisplayRole
                )

                self.update_grand_total()

            except ValueError:
                QMessageBox.warning(self, "Input Error",
                                    "Please enter valid numeric values for 'რაოდენობა', 'ერთეულის რაოდენობა', and 'პროდუქტის ღირებულება'.")
                self.update_grand_total()
            except ZeroDivisionError as zde:
                QMessageBox.warning(self, "Calculation Error",
                                    f"Calculation failed: {zde}. Check product unit quantity.")
                self.update_grand_total()
            except Exception as e:
                QMessageBox.critical(self, "Calculation Error", f"An unexpected error occurred: {e}")
                self.update_grand_total()


    def update_grand_total(self):
        total = 0.0
        for row in range(self.destinationModel.rowCount()):
            total_item = self.destinationModel.item(row, 4)  # Column 4 is 'სულ'
            if total_item and total_item.text():
                try:
                    # Add the total from each row
                    total += float(total_item.text())
                except ValueError:
                    # Silently ignore rows with invalid total values
                    pass

        # Update the text of the QLineEdit with the new grand total,
        # formatted to two decimal places.
        self.total_amount.setText(f"{total:.2f}")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            # Check if the event came from the merchant table
            if obj == self.merchant_table:
                if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                    self.paste_selected_row()
                    return True  # Event handled

            # Check if the event came from the basket table
            elif obj == self.basket:
                if event.key() == Qt.Key.Key_Delete:
                    self.delete_product()
                    return True  # Event handled

        return super().eventFilter(obj, event)

    def load_qss(self, filepath):
        """Loads a QSS file and applies it to the application."""
        qss_file = QFile(filepath)
        if not qss_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
            QMessageBox.critical(self, "QSS Error",
                                 f"Error: Could not open QSS file: {filepath}\n"
                                 f"Check file path and permissions.")
            return

        stylesheet = QTextStream(qss_file).readAll()
        qss_file.close()

        QApplication.instance().setStyleSheet(stylesheet)

    def load_data(self):
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    # 1. MODIFIED SQL: Select m."ATT_MAT" instead of n."COD_MAT"
                    cursor.execute("""
                    SELECT
                        m."NAM_MAT",          -- 0: პროდუქტის სახელი (Product Name)
                        n."PRICE",            -- 1: პროდუქტის ღირებულება (Price)
                        m."ATT_MAT",          -- 2: ATT_MAT string (used to get დღგ/რეცეპტით)
                        n."DAT_GOOD",         -- 3: ვარგისია
                        n."NAST",             -- 4: ნაშთი (Stock)
                        n."SER_NUM"           -- 5: სერიული ნომერი
                    FROM
                        public.mater1 AS m
                    JOIN
                        public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
                    """)

                    raw_data = cursor.fetchall()

                    # 2. PRE-PROCESS DATA to replace ATT_MAT string with translated values
                    processed_data = []
                    for row_data in raw_data:
                        # Extract the raw ATT_MAT string (now at index 2)
                        att_mat_string = row_data[2]

                        # Initialize translated field with default if translation fails
                        translated_field = ""

                        if att_mat_string and len(att_mat_string) >= 13:
                            # Extract the required attribute values (indices 6 and 12 are 0-based)
                            # NOTE: The attribute string indices are 1-based in your documentation:
                            # 'დღგ': attribute_value_str[6]
                            # 'რეცეპტით გაცემა': attribute_value_str[12]
                            # This corresponds to 0-based indices 6 and 12 in the string.

                            vat_code = att_mat_string[6]  # Index 6 for VAT (დღგ)
                            recipe_code = att_mat_string[12]  # Index 12 for Recipe (რეცეპტით გაცემა)

                            # Translate VAT
                            vat_display = 'იბეგრება' if vat_code == '1' else 'არ იბეგრება'

                            # Translate Recipe
                            recipe_display = 'რეცეპტით' if recipe_code == '1' else 'ურეცეპტო'

                            # Combine them for display in one column
                            translated_field = f"დღგ: {vat_display} / {recipe_display}"

                        # Build the new row:
                        # [Name, Price, Translated Field, Date, Stock, Serial]
                        new_row = [
                            row_data[0],  # NAM_MAT
                            row_data[4],  # NAST
                            row_data[1],  # PRICE
                            row_data[3],  # DAT_GOOD
                            translated_field,  # New combined field (replacing ATT_MAT)
                            row_data[5]  # SER_NUM
                        ]
                        processed_data.append(tuple(new_row))

                    # Use a dummy column_names list, as it's not strictly necessary for display
                    dummy_column_names = ['NAM_MAT', 'NAST', 'PRICE', 'DAT_GOOD', 'ATT_MAT_DISPLAY', 'SER_NUM']

                    self.display_source_data(processed_data, dummy_column_names)

        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to load data:\n{str(e)}")

    def display_source_data(self, data: List[tuple], column_headers: List[str]):
        self.sourceModel.clear()
        source_georgian_headers = [
            'სახელი',
            'ნაშთი',
            'ღირებულება',  # 3. UPDATED HEADER NAME
            'ვადა',
            'დღ/სპ',
            'სერიული ნომერი'
        ]
        self.sourceModel.setHorizontalHeaderLabels(source_georgian_headers)
        self.merchant_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.merchant_table.horizontalHeader().resizeSection(0, 430)
        self.merchant_table.horizontalHeader().resizeSection(1, 120)
        self.merchant_table.horizontalHeader().resizeSection(2, 140)
        self.merchant_table.horizontalHeader().resizeSection(3, 120)
        self.merchant_table.horizontalHeader().resizeSection(4, 250)
        self.merchant_table.horizontalHeader().resizeSection(5, 200)

        if data:
            self.sourceModel.beginInsertRows(QModelIndex(), 0, len(data) - 1)
            for row_data in data:
                # Note: row_data now contains the translated string at index 2

                # 1. Create the list of QStandardItems using a list comprehension
                row_items = [QStandardItem(str(cell_data)) for cell_data in row_data]

                # 2. Loop through the new list to set tooltips
                for i, item in enumerate(row_items):
                    # We use the original data in `row_data` for a more descriptive tooltip
                    cell_data = row_data[i]

                    if i == 0:  # Column for Product Name
                        item.setToolTip(f"პროდუქტის დასახელება: {cell_data}")
                    elif i == 4:  # New VAT/Recipe column
                        item.setToolTip(cell_data)
                    elif i == 5:  # Column for Serial Number
                        item.setToolTip(f"სერიული ნომერი: {cell_data}")

                self.sourceModel.appendRow(row_items)
            self.sourceModel.endInsertRows()

    def paste_selected_row(self):
        selected_indexes = self.merchant_table.selectionModel().selectedRows()

        if not selected_indexes:
            return

        selected_row_index_from_source = selected_indexes[0].row()

        product_name_item = self.sourceModel.item(selected_row_index_from_source, 0)
        price_item = self.sourceModel.item(selected_row_index_from_source, 2)
        product_dat = self.sourceModel.item(selected_row_index_from_source, 3).text()

        product_nast = self.sourceModel.item(selected_row_index_from_source, 1).text()
        date_now = datetime.date.today()
        # serial_number_item = self.sourceModel.item(selected_row_index_from_source, 5)
        # serial_number_text = serial_number_item.text() if serial_number_item else "N/A"
        try:
            if float(product_nast) == 0.0:
                QMessageBox.information(self,'Out of stock','პროდუქტი არ არის მარაგში.')
                return
            if product_dat.strip().lower() in ['', 'none', 'null']:
                # If the date is missing, we consider it expired or invalid
                QMessageBox.information(self, 'Product expired', 'პროდუქტი ვადაგასულია (ვადა არ არის მითითებული).')
                return
            expiration_date_from_db = datetime.datetime.strptime(product_dat, '%Y-%m-%d').date()
            if expiration_date_from_db < date_now or expiration_date_from_db == 'None':
                QMessageBox.information(self, 'Product expired', 'პროდუქტი ვადაგასულია.')
                return
        except ValueError as e:
            QMessageBox.warning(self, 'Error', f'Failed to process product data. Details: {e}')



        product_name_full = product_name_item.text() if product_name_item else ""
        price_str = price_item.text() if price_item else "0.0"

        # This is the original parsed quantity of internal units (e.g., 80 from #80ტ)
        product_unit_quantity_parsed_from_name = 0
        pattern = r'#(\d+)(?:ტ|ა|დრ)'
        match = re.search(pattern, product_name_full)

        if match:
            try:
                product_unit_quantity_parsed_from_name = int(match.group(1))
            except ValueError:
                product_unit_quantity_parsed_from_name = 0

        try:
            price = float(price_str)
        except ValueError:
            price = 0.0

        quantity_in_basket_initial = 0  # Initial customer quantity when adding to basket

        # Initial total calculation will use standard logic
        initial_total = quantity_in_basket_initial * price

        new_row_items = [
            QStandardItem(product_name_full),
            QStandardItem(str(quantity_in_basket_initial)),
            QStandardItem(f"{price:.2f}"),
            QStandardItem(str(0)),
            # This is the *initial* editable value for 'ერთეულის რაოდენობა'
            QStandardItem(f"{initial_total:.2f}")
        ]
        new_row_items[0].setToolTip(f"პროდუქტის დასახელება: {product_name_full}")
        # new_row_items[1].setToolTip(f"სერიული ნომერი: {serial_number_text}")
        # --- IMPORTANT NEW STEP ---
        # Store the original parsed product_unit_quantity in a hidden role (UserRole + 3)
        # for the 'ერთეულის რაოდენობა' column (index 3).
        # This allows `handle_basket_data_change` to retrieve the original 80 (from #80ტ)
        # even if the user later changes the displayed 'ერთეულის რაოდენობა' to 60.
        new_row_items[3].setData(product_unit_quantity_parsed_from_name, Qt.ItemDataRole.UserRole + 3)

        # Set read-only flags for specific columns
        new_row_items[0].setFlags(new_row_items[0].flags() & ~Qt.ItemFlag.ItemIsEditable)  # Product Name
        new_row_items[4].setFlags(new_row_items[4].flags() & ~Qt.ItemFlag.ItemIsEditable)  # Total
        sold_items = {
            new_row_items[0].text(): {
                'რაოდენობა': new_row_items[1].text(),
                'ფასი': new_row_items[2].text(),
                'ერთეულის რაოდენობა': new_row_items[3].text()
            }
        }
        self.destinationModel.appendRow(new_row_items)
        self.update_grand_total()
        return sold_items

    def checkout(self):
        sold_items = {}

        # We will get the total price from the grand total displayed on the UI
        total_price = float(self.total_amount.text())  # Assuming total_amount is a QLineEdit

        # 1. Loop through all rows to build a clean list of item data
        context_list = []
        for row in range(self.destinationModel.rowCount()):
            product_name = self.destinationModel.item(row, 0).text()
            quantity = self.destinationModel.item(row, 1).text()
            price = self.destinationModel.item(row, 2).text()
            unit_quantity = self.destinationModel.item(row, 3).text()

            # Build a dictionary for this item and add it to our list
            item_data = {
                'პროდუქტის სახელი': product_name,
                'რაოდენობა': quantity,
                'ერთეულის რაოდენობა': unit_quantity,
                'ფასი': price
            }
            context_list.append(item_data)

        invoice_number = random.randint(100000, 999999)
        created_date = datetime.date.today().strftime('%Y-%m-%d')
        created_time = datetime.datetime.now().strftime('%H:%M:%S')

        # 2. Create a single, comprehensive context dictionary for Jinja2
        invoice_context = {
            'invoice_number': invoice_number,
            'created_date': f'{created_date} / {created_time}',
            'items': context_list,
            'total_price': f"{total_price:.2f}"
        }

        # 3. Database Insertion (main logic)
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    # 1. Insert the main invoice record first
                    cursor.execute(
                        """
                        INSERT INTO invoices (invoice_id, username, total_price, created_at) 
                        VALUES (%s, %s, %s, %s)
                        """,
                        (invoice_number, self.current_username, total_price, f'{created_date}/{created_time}')
                    )

                    # 2. Insert each product into the 'operations' table
                    for item in context_list:
                        cursor.execute(
                            """
                            INSERT INTO operations (
                                invoice_id, product_name, quantity, item_quantity, product_price, date
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (invoice_number, item['პროდუქტის სახელი'], float(item['რაოდენობა']),
                             item['ერთეულის რაოდენობა'],
                             float(item['ფასი']), f'{created_date}/{created_time}')
                        )
                    conn.commit()
                    self.load_data()
        except Exception as db_insert_e:
            QMessageBox.critical(self, "Database Error", f"ინვოისის მონაცემების შენახვა ვერ მოხერხდა: {db_insert_e}")
            logging.error(f"Invoice insertion failed for {invoice_number}: {db_insert_e}")
            return  # Exit checkout if essential data cannot be saved

        folder_name = "invoices"
        target_folder = pathlib.Path(folder_name)
        target_folder.mkdir(parents=True, exist_ok=True)

        # 4. PDF Generation
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

                # Ensure wkhtmltopdf is installed and the path is correct
                config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
                pdfkit.from_string(output_text, full_path, configuration=config)

            except Exception as e:
                # Catch PDF creation errors
                QMessageBox.warning(self, 'Invoice creation Error', f'ქვითრის შექმნა ვერ მოხერხდა: {e}')

        # 5. Stock Update
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

                            # Find the product's COD_MAT (code) from mater1 table
                            cursor.execute(
                                "SELECT \"COD_MAT\" FROM public.mater1 WHERE \"NAM_MAT\" = %s",
                                (product_name,)
                            )
                            cod_mat = cursor.fetchone()

                            if cod_mat:
                                # Use the COD_MAT to update the quantity in the nashti table
                                cursor.execute(
                                    """
                                    UPDATE public.nashti 
                                    SET "NAST" = "NAST" - %s 
                                    WHERE "COD_MAT" = %s
                                    """,
                                    (quantity_sold, cod_mat[0])
                                )
                            else:
                                logging.warning(
                                    f"Product '{product_name}' not found in database. Stock not updated.")

                        conn.commit()
                        self.load_data()
                QMessageBox.information(self, "Success", "მონაცემები წარმატებით განახლდა!")
                logging.info(f"Database updated for checkout. Invoice: {invoice_number}")
            except Exception as db_e:
                QMessageBox.critical(self, "Database Error", f"მონაცემების განახლება ვერ მოხერხდა: {db_e}")
                logging.error(f"Database update failed for invoice {invoice_number}: {db_e}")

        logging.info(f"Checkout successful. Username: {self.current_username} . Invoice created: {full_path}")

        # 6. Printing
        if os.path.exists(full_path):
            reply = QMessageBox.question(self, 'ინვოისის ამობეჭდვა', 'ინვოისი წარმატებით შეიქმნა!, გსურთ ამობეჭდვა?',
                                         QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                # --- CRITICAL FIX 2: Correct structure for file opening error handling ---
                try:
                    os.startfile(full_path)
                except Exception as e:
                    QMessageBox.critical(self, "Print Error", f"ინვოისის გახსნა ვერ მოხერხდა: {e}")
                # --- End of Fix 2 ---
        else:
            # Only show this if PDF creation was attempted but file not found
            if invoice_creation == QMessageBox.StandardButton.Yes:
                QMessageBox.warning(self, "Print Error", "ქვითრის ფაილი ვერ მოიძებნა ამოსაბეჭდად.")

        self.destinationModel.setRowCount(0)
        self.total_amount.clear()

    def delete_product(self):
        selected_indexes = self.basket.selectionModel().selectedRows()
        if selected_indexes:
            # Get the row index of the first selected item
            row_to_delete = selected_indexes[0].row()

            # Add a print statement to confirm the function is running
            # print(f"Deleting row: {row_to_delete}")

            # Remove the row from the model
            self.destinationModel.removeRow(row_to_delete)

            # Recalculate the grand total after deleting the row
            self.update_grand_total()
            QMessageBox.information(self, "Success", "პროდუქტი წარმატებით წაიშალა!")
        else:
            # If no row is selected, show a warning message
            QMessageBox.warning(self, "Selection Error", "გთხოვთ აირჩიოთ წასაშლელი პროდუქტი.")

    def selected_product_info(self):
        # 1. Get the list of selected QModelIndex objects (one for each selected row)
        selected_indexes = self.basket.selectionModel().selectedRows()

        if not selected_indexes:
            # Display warning if no row is selected
            QMessageBox.warning(self, "Selection Error", "გთხოვთ აირჩიოთ პროდუქტი.")
            return None  # Must return None, not the result of QMessageBox

        # 2. Get the row number from the first selected index
        selected_row = selected_indexes[0].row()

        # 3. Use the row number to get the QStandardItem from the model (Column 0: Product Name)
        product_name_item = self.destinationModel.item(selected_row, 0)

        # 4. Extract the text (product name)
        if product_name_item:
            selected_product_name = product_name_item.text()
            return selected_product_name

        return None
