import datetime
import os
from user_system import UserSystem
import logging
import jinja2
import pdfkit
import random
import psycopg2
from PyQt6.QtCore import Qt, QEvent, QModelIndex, QTextStream, QFile, QIODevice
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (QWidget, QMessageBox, QLineEdit, QComboBox,
                             QTextEdit, QTableWidget, QCheckBox, QTableView, QHeaderView, QApplication)
from PyQt6.uic import loadUi
from typing import List, Union, Dict, Any
from user_system import UserSystem
import re
from return_function import ReturnProduct

from database import Database
db = Database()


class MaterTable(QWidget):
    """Product management interface with database integration"""

    def __init__(self, user_db: UserSystem = None):
        super().__init__()
        loadUi("ui/add_product.ui", self)

        # Initialize database connection
        self.user_db = UserSystem()

        # Setup UI components and validation
        self.setup_ui()
        self.setup_connections()

        # Set initial state
        self.save_button.setEnabled(False)

    def setup_ui(self) -> None:
        """Initialize UI components and dropdowns"""
        # self.category.addItems(['მედიკამენტი', 'არამედიკამენტი'])

        # Define mandatory fields for validation
        self.mandatory_fields = [
            self.name,
            self.division,
            self.cc,
            self.rec,
            self.spec_code
        ]

    def setup_connections(self) -> None:
        """Connect UI signals to slots"""
        self.save_button.clicked.connect(self.save_data)

        # Connect field validation
        for field in self.mandatory_fields:
            if isinstance(field, (QLineEdit, QComboBox, QTextEdit)):
                if isinstance(field, QComboBox):
                    field.currentTextChanged.connect(self.validate_fields)
                else:
                    field.textChanged.connect(self.validate_fields)

    def validate_fields(self) -> None:
        """Enable save button only when all mandatory fields are valid"""
        all_valid = all(
            field.currentText().strip() if isinstance(field, QComboBox)
            else field.text().strip()
            for field in self.mandatory_fields
        )
        self.save_button.setEnabled(all_valid)

    def get_form_data(self) -> Dict[str, Any]:
        """Collect and validate all form data"""
        return {
            'code': self._generate_unique_code(),
            'name': self.name.text().strip(),
            'division': self.division.text().strip(),
            'type': self.category.currentText(),
            'cc': self.cc.currentText().strip() if isinstance(self.cc, QComboBox)
            else self.cc.text().strip(),
            'rec': self.rec.currentText().strip() if isinstance(self.rec, QComboBox)
            else self.rec.text().strip(),
            'referral': self.referral.text().strip(),
            'generic': self.generic.text().strip(),
            'storecon': self.storecon.text().strip(),
            'hc': self._generate_unique_code(),
            'hc2': self._generate_unique_code(),
            'note': self.note.toPlainText().strip() if hasattr(self.note, 'toPlainText')
            else self.note.text().strip(),
            'spec_code': self.spec_code.text().strip()
        }

    def _generate_unique_code(self, length: int = 5) -> str:
        """Generate a random numeric code"""
        return ''.join(random.choices('0123456789', k=length))

    def save_data(self) -> None:
        """Save product data to database with comprehensive error handling"""
        try:
            product_data = self.get_form_data()

            with db.connect() as conn:
                with conn.cursor() as cursor:
                    try:
                        cursor.execute('''
                            INSERT INTO mater (
                                code, name, division, type, cc, rec, referral,
                                generic, storecon, hc, hc2, note, spec_code
                            ) VALUES (
                                %(code)s, %(name)s, %(division)s, %(type)s, 
                                %(cc)s, %(rec)s, %(referral)s, %(generic)s,
                                %(storecon)s, %(hc)s, %(hc2)s, %(note)s, %(spec_code)s
                            )
                        ''', product_data)
                        conn.commit()

                        QMessageBox.information(
                            self, "Success",
                            "Product saved successfully!"
                        )
                        self.clear_form()

                    except psycopg2.IntegrityError as e:
                        conn.rollback()
                        self._handle_integrity_error(e, product_data)

        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"An unexpected error occurred: {str(e)}"
            )

    def _handle_integrity_error(self, error: psycopg2.IntegrityError,
                                product_data: Dict[str, Any]) -> None:
        """Handle database integrity errors appropriately"""
        error_msg = str(error)

        if 'mater_code_key' in error_msg:
            QMessageBox.warning(
                self, "Duplicate Code",
                "This product code already exists. Please try again."
            )
        elif 'mater_division_key' in error_msg:
            self._handle_duplicate_division(product_data)
        elif 'mater_spec_code_key' in error_msg:
            QMessageBox.warning(
                self, "Duplicate Spec Code",
                "This specification code already exists. Please use a different code."
            )
        else:
            QMessageBox.critical(
                self, "Database Error",
                f"Could not save product: {error_msg}"
            )

    def _handle_duplicate_division(self, product_data: Dict[str, Any]) -> None:
        """Provide options when encountering duplicate division"""
        response = QMessageBox.question(
            self, "Duplicate Division",
            f"Division '{product_data['division']}' already exists.\n"
            "Would you like to update the existing record?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if response == QMessageBox.StandardButton.Yes:
            self._update_existing_product(product_data)
        else:
            QMessageBox.information(
                self, "Operation Cancelled",
                "Please modify the division and try again."
            )

    def _update_existing_product(self, product_data: Dict[str, Any]) -> None:
        """Update existing product record"""
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE mater SET
                            name = %(name)s,
                            type = %(type)s,
                            cc = %(cc)s,
                            rec = %(rec)s,
                            referral = %(referral)s,
                            generic = %(generic)s,
                            storecon = %(storecon)s,
                            note = %(note)s,
                            spec_code = %(spec_code)s
                        WHERE division = %(division)s
                        RETURNING id
                    ''', product_data)

                    if cursor.rowcount > 0:
                        conn.commit()
                        QMessageBox.information(
                            self, "Success",
                            "Existing product updated successfully!"
                        )
                        self.clear_form()
                    else:
                        QMessageBox.warning(
                            self, "Not Found",
                            "No matching product found to update"
                        )
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Could not update product: {str(e)}"
            )

    def clear_form(self) -> None:
        """Reset all form fields to default state"""
        for field in self.mandatory_fields:
            if isinstance(field, QLineEdit):
                field.clear()
            elif isinstance(field, QComboBox):
                field.setCurrentIndex(0)

        # Clear optional fields
        self.referral.clear()
        self.generic.clear()
        self.storecon.clear()

        if hasattr(self.note, 'clear'):
            self.note.clear()

        # Reset focus
        self.name.setFocus()


class MaterTableView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel()
        loadUi('ui/view_mater.ui', self)
        self.load_data()
        self.tableView.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.btn_save.clicked.connect(self.save_changes)
        self.filter_name.textChanged.connect(self.filter_item_with_name)
        self.filter_generic.textChanged.connect(self.filter_item_with_generic)
        self.filter_code.textChanged.connect(self.filter_item_with_code)

    def load_data(self):
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, code, division, type,
                        cc, rec, referral, generic, storecon,
                        hc, hc2, note, spec_code, 
                        to_char(created_at, 'YY-MM-DD HH24:MI') as created_at
                        FROM mater
                    """)
                    self.display_mater(cursor.fetchall())
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to load data:\n{str(e)}")

    def display_mater(self, mater: List[tuple]):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(
            ['ID', 'Name', 'Code', 'Division', 'Type', 'CC', 'Rec', 'Referral', 'Generic', 'Storecon',
             'Hc', 'Hc2', 'Note', 'Spec_code', 'Created_at']
        )

        for product in mater:
            row = []
            for item in product:
                cell = QStandardItem(str(item))
                row.append(cell)
            self.model.appendRow(row)

        self.tableView.setModel(self.model)
        self.tableView.hideColumn(0) #Hiding Column you want to hide.

    def save_changes(self):
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    for row in range(self.model.rowCount()):
                        id = self.model.item(row, 0).text()
                        name = self.model.item(row, 1).text()
                        code = self.model.item(row, 2).text()
                        division = self.model.item(row, 3).text()
                        type = self.model.item(row, 4).text()
                        cc = self.model.item(row, 5).text()
                        rec = self.model.item(row, 6).text()
                        referral = self.model.item(row, 7).text()
                        generic = self.model.item(row, 8).text()
                        storecon = self.model.item(row, 9).text()
                        note = self.model.item(row, 12).text()

                        cursor.execute("""
                            UPDATE mater SET
                                name = %s,
                                code = %s,
                                division = %s,
                                type = %s, 
                                cc = %s,
                                rec = %s,
                                referral = %s,
                                generic = %s,
                                storecon = %s,
                                note = %s
                            WHERE id = %s
                        """, (name, code, division, type, cc, rec, referral, generic, storecon, note, id))
                    conn.commit()
                    QMessageBox.information(self, 'Successes', 'Changes saved successfully')

            self.model.clear()
            self.load_data()
            self.tableView.hideColumn(0)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to save changes:\n{str(e)}")


    def filter_item_with_name(self):
        filter_text = self.filter_name.text().lower()
        self._apply_filter(filter_text, column=1)  # Column 1 is Name

    def filter_item_with_generic(self):
        filter_text = self.filter_generic.text().lower()
        self._apply_filter(filter_text, column=8)  # Column 8 is Generic

    def filter_item_with_code(self):
        filter_text = self.filter_code.text().lower()
        self._apply_filter(filter_text, column=13)  # Column 2 is Code

    def _apply_filter(self, filter_text, column):
        """Helper method to apply filtering to a specific column"""
        for row in range(self.model.rowCount()):
            item = self.model.item(row, column)
            match = item is not None and filter_text in item.text().lower()
            self.tableView.setRowHidden(row, not match)



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
        self.merchant_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.merchant_table.resizeColumnsToContents()  # Often conflicts with Stretch, keep if specific columns are too wide/narrow
        # self.merchant_table.horizontalHeader().setStretchLastSection(True) # Only if you want last section to take all remaining space
        self.current_username = current_username
        self.basket.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Ensure the basket table cells are editable by double-click
        # Default is usually QAbstractItemView.DoubleClicked or EditKeyPressed
        # If your cells are not editable, you might explicitly set:
        # self.basket.setEditTriggers(QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.AnyKeyPressed)

        self.merchant_table.doubleClicked.connect(self.paste_selected_row)
        self.merchant_table.installEventFilter(self)

        # --- Set the desired headers for the DESTINATION table (basket) ---
        self.destinationModel.setHorizontalHeaderLabels([
            'სახელი',  # Column 0: Display only
            'რაოდენობა',  # Column 1: Editable (customer_qty)
            'ღირებულება',  # Column 2: Editable (product_unit_price)
            'ერთეულის რაოდენობა',  # Column 3: Editable (sold_internal_units)
            'სულ'  # Column 4: Calculated, not directly editable by user
        ])
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
        self.basket.resizeColumnsToContents()
        self.checkout_button.clicked.connect(self.checkout)
        self.delete_button.clicked.connect(self.delete_product)
        self.basket.installEventFilter(self)
        self.return_2.clicked.connect(self.show_return_table)

    def show_return_table(self):
        self.return_table = ReturnProduct()
        self.return_table.showMaximized()

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
                    cursor.execute("""
                    SELECT
                        m."NAM_MAT",          -- 0: პროდუქტის სახელი (Product Name)
                        n."PRICE",            -- 1: პროდუქტის ღირებულება (Price)
                        n."COD_MAT",          -- 2: დღ/სპ
                        n."DAT_GOOD",         -- 3: ვარგისია
                        n."NAST",             -- 4: ნაშთი (Stock)
                        n."SER_NUM"           -- 5: სერიული ნომერი
                    FROM
                        public.mater1 AS m
                    JOIN
                        public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
                    """)
                    column_names = [desc[0] for desc in cursor.description]
                    self.display_source_data(cursor.fetchall(), column_names)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to load data:\n{str(e)}")

    def display_source_data(self, data: List[tuple], column_headers: List[str]):
        self.sourceModel.clear()
        source_georgian_headers = [
            'სახელი',
            'ღირებულება',
            'დღ/სპ',
            'ვარგისია',
            'ნაშთი',
            'სერიული ნომერი'
        ]
        self.sourceModel.setHorizontalHeaderLabels(source_georgian_headers)

        if data:
            self.sourceModel.beginInsertRows(QModelIndex(), 0, len(data) - 1)
            for row_data in data:
                # 1. Create the list of QStandardItems using a list comprehension
                row_items = [QStandardItem(str(cell_data)) for cell_data in row_data]

                # 2. Loop through the new list to set tooltips
                for i, item in enumerate(row_items):
                    # We use the original data in `row_data` for a more descriptive tooltip
                    cell_data = row_data[i]

                    if i == 0:  # Column for Product Name
                        item.setToolTip(f"პროდუქტის დასახელება: {cell_data}")
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
        price_item = self.sourceModel.item(selected_row_index_from_source, 1)
        product_dat = self.sourceModel.item(selected_row_index_from_source, 3).text()

        product_nast = self.sourceModel.item(selected_row_index_from_source, 4).text()
        date_now = datetime.date.today()
        # serial_number_item = self.sourceModel.item(selected_row_index_from_source, 5)
        # serial_number_text = serial_number_item.text() if serial_number_item else "N/A"
        # try:
        #     if float(product_nast) == 0.0:
        #         QMessageBox.information(self,'Out of stock','პროდუქტი არ არის მარაგში.')
        #         return
        #     if product_dat.strip().lower() in ['', 'none', 'null']:
        #         # If the date is missing, we consider it expired or invalid
        #         QMessageBox.information(self, 'Product expired', 'პროდუქტი ვადაგასულია (ვადა არ არის მითითებული).')
        #         return
        #     expiration_date_from_db = datetime.datetime.strptime(product_dat, '%Y-%m-%d').date()
        #     if expiration_date_from_db < date_now or expiration_date_from_db == 'None':
        #         QMessageBox.information(self, 'Product expired', 'პროდუქტი ვადაგასულია.')
        #         return
        # except ValueError as e:
        #     QMessageBox.warning(self, 'Error', f'Failed to process product data. Details: {e}')



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
        # Optional: Print for verification (uses last_added_row_index as discussed)
        # last_added_row_index = self.destinationModel.rowCount() - 1
        # if last_added_row_index >= 0:
        #     qty_item_new = self.destinationModel.item(last_added_row_index, 1)
        #     unit_qty_item_new = self.destinationModel.item(last_added_row_index, 3)
        #     if qty_item_new and unit_qty_item_new:
        #         print(f"Added - Qty: {qty_item_new.text()}, Unit Qty (Editable): {unit_qty_item_new.text()}, Original Parsed Unit Qty: {unit_qty_item_new.data(Qt.ItemDataRole.UserRole + 3)}")
        # --- End of paste_selected_row changes ---


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
            'invoice_number': invoice_number,  # Replace with a real invoice number
            'created_date': f'{created_date} / {created_time}',
            'items': context_list,  # This is the list we will loop through in HTML
            'total_price': f"{total_price:.2f}"
        }
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

                # 2. Update stock and insert each product into the 'operations' table
                for item in context_list:
                    product_name = item['პროდუქტის სახელი']
                    quantity_sold = int(item['რაოდენობა'])
                    # Insert a row for each item in the 'operations' table
                    cursor.execute(
                        """
                        INSERT INTO operations (
                            invoice_id, product_name, quantity, item_quantity, product_price, date
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (invoice_number, item['პროდუქტის სახელი'], quantity_sold, item['ერთეულის რაოდენობა'],
                         float(item['ფასი']), f'{created_date}/{created_time}')
                    )
                conn.commit()
        #
        # 3. Move the PDF generation logic OUTSIDE the loop, and only run it once.
        try:
            template_loader = jinja2.FileSystemLoader('./')
            template_env = jinja2.Environment(loader=template_loader)
            template = template_env.get_template('invoice.html')
            output_text = template.render(invoice_context)

            # Ensure wkhtmltopdf is installed and the path is correct
            config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
            filename = f'Invoice({created_date})#{invoice_number}.pdf'
            full_path = os.path.join('invoices', filename)
            pdfkit.from_string(output_text, full_path,
                               configuration=config)
            database_changes = QMessageBox.question(self, 'მონაცემთა ბაზაში ცვლილებების შეტანა', 'შევიტანო ბაზაში ცვლილებები?',
                                                    QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
            if database_changes == QMessageBox.StandardButton.Yes:
                # --- START OF CORRECTED CODE FOR DATABASE UPDATE ---
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
                    QMessageBox.information(self, "Success", "მონაცემები წარმატებით განახლდა!")
                    logging.info(f"Database updated for checkout. Invoice: {invoice_number}")
                except Exception as db_e:
                    QMessageBox.critical(self, "Database Error", f"მონაცემების განახლება ვერ მოხერხდა: {db_e}")
                    logging.error(f"Database update failed for invoice {invoice_number}: {db_e}")
                # --- END OF CORRECTED CODE ---
            logging.info(f"Checkout successful. Username: {self.current_username} . Invoice created: {full_path}")
            reply = QMessageBox.question(self, 'ინვოისის ამობეჭდვა', 'ინვოისი წარმატებით შეიქმნა!, გსურთ ამობეჭდვა?',
                                         QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No )
            # QMessageBox.standardButton(self, "PDF Created", "ინვოისი წარმატებით შეიქმნა!")
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(full_path)
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"ინვოისის შექმნა ვერ მოხერხდა: {e}")

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
