# from PyQt6.QtGui.QTextCursor import position
from threading import current_thread

from PyQt6.QtCore import QFile, QIODevice, QTextStream, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QLabel, QWidget
from PyQt6.uic import loadUi
import sys
import json
import psycopg2
import bcrypt
from main_menu import MenuWindow, UserRegistration
from user_system import UserSystem, RecoverPass

from database import Database
db = Database()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('ui/LoginWindow.ui', self)
        self.load_qss('ui/Adaptic.qss')
        self.is_first_run()
        self.version = self.get_version()
        self.user_system = UserSystem()
        self.main_menu = None
        self.username_input.setFocus()
        # Connect signals
        self.login_button.clicked.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        self.initial_setup.clicked.connect(self.initialize_databases)
        self.pass_restore.setOpenExternalLinks(False)
        self.pass_restore.linkActivated.connect(self.show_password_form)
        self.password_form = RecoverPass()
        self.setWindowFlags(Qt.WindowType.CustomizeWindowHint |
                            Qt.WindowType.WindowCloseButtonHint |
                            Qt.WindowType.WindowMinimizeButtonHint)

    def is_first_run(self):
        with open("settings.json", "r") as file:
            settings = json.load(file)
        if settings["first_run"] == "No":
            self.initial_setup.hide()
        else:
            QMessageBox.information(self, "პროგრამის პირველი გაშვება",
                                    "საჭიროა მონაცემთა ბაზის ინიციალიზაცია!")
    def get_version(self):
        with open("settings.json", "r") as file:
            settings = json.load(file)
            version = settings["version"]

            return version

    def _hash_password(self, password):
        """Hash a password for storage"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def initialize_databases(self):
        QMessageBox.information(self, "ინიციალიზაცია",
                                "მიმდინარეობს მონაცემთა ბაზების ინიციალიზაცია პირველი გაშვებისთვის.")

        try:
            hashed_pw = self._hash_password("123")
            with db.connect() as conn:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(255) UNIQUE NOT NULL,
                            password TEXT NOT NULL,
                            email VARCHAR(255) UNIQUE,
                            phone VARCHAR(20) UNIQUE,
                            position VARCHAR(100) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        ''')
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
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS public.invoices (
                            invoice_id INT PRIMARY KEY,
                            username VARCHAR(255),
                            total_price NUMERIC(10, 2),
                            created_at TIMESTAMP WITH TIME ZONE
                            );
                        ''')
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS public.operations (
                            id SERIAL PRIMARY KEY,
                            invoice_id INT REFERENCES public.invoices(invoice_id),
                            product_name VARCHAR(255),
                            quantity NUMERIC(10, 2),
                            item_quantity VARCHAR(255),
                            product_price NUMERIC(10, 2),
                            date TIMESTAMP WITH TIME ZONE
                            );
                        ''')
                    cursor.execute('''
                        INSERT INTO users 
                        (username, password, email, phone, position) 
                        VALUES (%s, %s, %s, %s, %s)
                        ''',
                        ("root", hashed_pw.decode(), "email", "phone", "root"))

                    self._add_missing_columns(cursor)
                    QMessageBox.information(self, "ინიციალიალიზაცია დასრულდა",
                                            "მონაცემთა ბაზები დაინიცირდა,\n"
                                            "პროგრამა მზადაა გასაშვებად.")
                    self.update_settings_file()
                    self.initial_setup.hide()
        except psycopg2.Error as e:
            print(f"Database initialization error: {e}")

    def update_settings_file(self):
        with open("settings.json", "r") as file:
            settings = json.load(file)
        settings["first_run"] = "No"

        with open("settings.json", "w") as file:
            json.dump(settings, file, indent=4)

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

    def show_password_form(self):
        self.password_form.show()

    def handle_login(self):
        """Handle login process with position-based permissions"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, 'Input Error', 'Please enter both username and password')
            return

        try:
            success, position = self.user_system.login(username, password)

            if success:
                self.main_menu = MenuWindow(username=username, login_window=self)
                self.main_menu.setWindowTitle(f"მელოდია {self.version} - {username} ({position})")
                # Set permissions based on position
                if position == "ადმინისტრატორი" or position == "root":
                    self.main_menu.action_users.setEnabled(True)
                    self.main_menu.action_register.setEnabled(True)
                self.main_menu.showMaximized()
                self.hide()

            else:
                QMessageBox.warning(self, 'Login Failed', 'Invalid username or password')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Login failed: {str(e)}')

    def closeEvent(self, event):
        """Handle application exit"""
        if self.main_menu:
            self.main_menu.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
