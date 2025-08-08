import datetime
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

        # Initialize database schema
        self._initialize_db()

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

    def _initialize_db(self) -> None:
        """Initialize database schema with proper error handling"""
        try:
            with db.connect() as conn:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS mater (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            code VARCHAR(255) UNIQUE NOT NULL,
                            division VARCHAR(255) NOT NULL,
                            type VARCHAR(255) NOT NULL,
                            cc VARCHAR(255) NOT NULL,
                            rec VARCHAR(20) NOT NULL,
                            referral VARCHAR(100) NOT NULL,
                            generic VARCHAR(100) NOT NULL,
                            storecon VARCHAR(100) NOT NULL,
                            hc VARCHAR(100) UNIQUE NOT NULL,
                            hc2 VARCHAR(100) UNIQUE NOT NULL,
                            note TEXT,
                            spec_code VARCHAR(100) UNIQUE NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    # Add any missing columns
                    self._add_missing_columns(cursor)
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Database Error",
                                 f"Could not initialize database: {e}")

    def _add_missing_columns(self, cursor) -> None:
        """Ensure all required columns exist in the table"""
        columns_to_add = [
            ('name', 'VARCHAR(255) NOT NULL DEFAULT \'\''),
            ('note', 'TEXT')
        ]

        for column, definition in columns_to_add:
            try:
                cursor.execute(f'''
                    ALTER TABLE mater 
                    ADD COLUMN IF NOT EXISTS {column} {definition}
                ''')
            except psycopg2.Error:
                pass  # Column already exists with different definition

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
    #
    # def get_db_connection(self):
    #     """Establish database connection with error handling"""
    #     try:
    #         return psycopg2.connect(
    #             host="localhost",
    #             dbname="melodia",
    #             user="melodia",
    #             password="melo",
    #             port=5432
    #         )
    #     except Exception as e:
    #         QMessageBox.critical(self, "Database Error",
    #                              f"Connection failed: {str(e)}")
    #         raise

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
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi('ui/merchant.ui', self)
        self.sourceModel = QStandardItemModel()
        self.destinationModel = QStandardItemModel()
        self.merchant_table.setModel(self.sourceModel)
        self.filter_name.textChanged.connect(self.filter_item_with_name)
        self.merchant_table.setModel(self.sourceModel)
        self.basket.setModel(self.destinationModel)

        self.merchant_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.merchant_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.merchant_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.merchant_table.resizeColumnsToContents()  # Often conflicts with Stretch, keep if specific columns are too wide/narrow
        #         # self.merchant_table.horizontalHeader().setStretchLastSection(True) # Only if you want last section to take all remaining space

        self.basket.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Ensure the basket table cells are editable by double-click
        # Default is usually QAbstractItemView.DoubleClicked or EditKeyPressed
        # If your cells are not editable, you might explicitly set:
        # self.basket.setEditTriggers(QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.AnyKeyPressed)

        self.merchant_table.doubleClicked.connect(self.paste_selected_row)
        self.merchant_table.installEventFilter(self)

        # --- Set the desired headers for the DESTINATION table (basket) ---
        self.destinationModel.setHorizontalHeaderLabels([
            'პროდუქტის სახელი',  # Column 0: Display only
            'რაოდენობა',  # Column 1: Editable (customer_qty)
            'პროდუქტის ღირებულება',  # Column 2: Editable (product_unit_price)
            'ერთეულის რაოდენობა',  # Column 3: Editable (sold_internal_units)
            'სულ'  # Column 4: Calculated, not directly editable by user
        ])
        # --- End of destination header setup ---

        # Connect the dataChanged signal of the destinationModel
        # This will now handle updates for changes in Quantity, Price, OR Unit Quantity
        self.destinationModel.dataChanged.connect(self.handle_basket_data_change)

        self.load_qss('ui/Adaptic.qss')
        self.load_data()
        self.basket.resizeColumnsToContents()
        

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
        sold_internal_units_col_idx = 3  # This is the user-editable 'ერთეულის რაოდენობა'
        total_col_idx = 4

        # Important: The calculation should happen if the user changes QUANTITY, PRICE, OR UNIT_QUANTITY
        if changed_col in [customer_qty_col_idx, product_unit_price_col_idx, sold_internal_units_col_idx]:
            try:
                # 1. Get customer's desired quantity of product units (რაოდენობა)
                customer_qty_item = self.destinationModel.item(changed_row, customer_qty_col_idx)
                customer_qty_str = customer_qty_item.text() if customer_qty_item else "0"
                customer_qty = int(customer_qty_str)

                # 2. Get the editable unit quantity (ერთეულის რაოდენობა)
                sold_internal_units_item = self.destinationModel.item(changed_row, sold_internal_units_col_idx)
                sold_internal_units_str = sold_internal_units_item.text() if sold_internal_units_item else "0"
                sold_internal_units = int(sold_internal_units_str)


                # 3. Get the original parsed product_unit_quantity (e.g., 80 from #80ტ)
                # This value was stored in UserRole + 3 when the row was first added.
                original_parsed_product_total_internal_units = sold_internal_units_item.data(
                    Qt.ItemDataRole.UserRole + 3)
                if original_parsed_product_total_internal_units is None:
                    original_parsed_product_total_internal_units = 0  # Default if not found/stored

                # 4. Get the price per product unit (პროდუქტის ღირებულება)
                price_item = self.destinationModel.item(changed_row, product_unit_price_col_idx)
                price_str = price_item.text() if price_item else "0.0"
                product_unit_price = float(price_str)

                new_total = 0.0  # Initialize total

                # Apply the special calculation rule based on your clarified logic:
                # Condition:
                # 1. 'რაოდენობა' (customer_qty) is 1
                # 2. The original parsed 'ერთეულის რაოდენობა' (original_parsed_product_total_internal_units) is more than 0
                # 3. The user-edited 'ერთეულის რაოდენობა' (sold_internal_units) is not equal the original parsed quantity
                if (customer_qty == 1 and
                        original_parsed_product_total_internal_units > 0 and
                        sold_internal_units > 0 and  # Ensure sold_internal_units is also positive for valid calculations
                        sold_internal_units != original_parsed_product_total_internal_units):

                    # Calculate price per individual internal item
                    # This could cause ZeroDivisionError if original_parsed_product_total_internal_units is 0
                    if original_parsed_product_total_internal_units == 0:
                        raise ZeroDivisionError(
                            "Original product unit quantity cannot be zero for partial sale calculation.")

                    price_per_internal_item = product_unit_price / original_parsed_product_total_internal_units

                    # Total is then price per internal item * number of internal items being sold
                    new_total = price_per_internal_item * sold_internal_units
                    total_amount = 0.0



                else:
                    # Standard calculation for all other cases:
                    # (number of product units) * (price per product unit)
                    new_total = customer_qty * product_unit_price

                # Update the 'სულ' (Total) column in the same row
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
        if obj == self.merchant_table and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.paste_selected_row()
                return True
        return super().eventFilter(obj, event)

    # def get_db_connection(self):
    #     """Establish database connection with error handling"""
    #     try:
    #         return psycopg2.connect(
    #             host="localhost",
    #             dbname="melodia",
    #             user="melodia",
    #             password="melo",
    #             port=5432
    #         )
    #     except Exception as e:
    #         QMessageBox.critical(self, "Database Error",
    #                              f"Connection failed: {str(e)}")
    #         raise

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
                        n."DAT_PROD",         -- 3: ვარგისია
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

    # def display_source_data(self, data: List[tuple], column_headers: List[str]):
    #     self.sourceModel.clear()
    #     source_georgian_headers = [
    #         'პროდუქტის სახელი',
    #         'პროდუქტის ღირებულება',
    #         'დღ/სპ',
    #         'ვარგისია',
    #         'ნაშთი',
    #         'სერიული ნომერი'
    #     ]
    #     self.sourceModel.setHorizontalHeaderLabels(source_georgian_headers)
    #
    #     if data:
    #         self.sourceModel.beginInsertRows(QModelIndex(), 0, len(data) - 1)
    #         for row_data in data:
    #             row_items = [QStandardItem(str(cell_data)) for cell_data in row_data]
    #             self.sourceModel.appendRow(row_items)
    #         self.sourceModel.endInsertRows()

    def display_source_data(self, data: List[tuple], column_headers: List[str]):
        self.sourceModel.clear()
        source_georgian_headers = [
            'პროდუქტის სახელი',
            'პროდუქტის ღირებულება',
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

        quantity_in_basket_initial = 1  # Initial customer quantity when adding to basket

        # Initial total calculation will use standard logic
        initial_total = quantity_in_basket_initial * price

        new_row_items = [
            QStandardItem(product_name_full),
            QStandardItem(str(quantity_in_basket_initial)),
            QStandardItem(f"{price:.2f}"),
            QStandardItem(str(product_unit_quantity_parsed_from_name)),
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

        self.destinationModel.appendRow(new_row_items)
        self.update_grand_total()

        # Optional: Print for verification (uses last_added_row_index as discussed)
        # last_added_row_index = self.destinationModel.rowCount() - 1
        # if last_added_row_index >= 0:
        #     qty_item_new = self.destinationModel.item(last_added_row_index, 1)
        #     unit_qty_item_new = self.destinationModel.item(last_added_row_index, 3)
        #     if qty_item_new and unit_qty_item_new:
        #         print(f"Added - Qty: {qty_item_new.text()}, Unit Qty (Editable): {unit_qty_item_new.text()}, Original Parsed Unit Qty: {unit_qty_item_new.data(Qt.ItemDataRole.UserRole + 3)}")
        # --- End of paste_selected_row changes ---




