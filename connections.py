import random
import psycopg2
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (QWidget, QMessageBox, QLineEdit, QComboBox,
                             QTextEdit, QTableWidget, QCheckBox, QTableView, QHeaderView)
from PyQt6.uic import loadUi
from typing import List, Union, Dict, Any
from user_system import UserSystem


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
            with self.user_db._get_connection() as conn:
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

            with self.user_db._get_connection() as conn:
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
            with self.user_db._get_connection() as conn:
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
        # self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # self.btn_save.clicked.connect(self.save_changes)

    def get_db_connection(self):
        """Establish database connection with error handling"""
        try:
            return psycopg2.connect(
                host="localhost",
                dbname="postgres",
                user="postgres",
                password="Eleneliza1984",
                port=5432
            )
        except Exception as e:
            QMessageBox.critical(self, "Database Error",
                                 f"Connection failed: {str(e)}")
            raise

    def load_data(self):
        try:
            with self.get_db_connection() as conn:
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






