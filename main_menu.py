import bcrypt
import psycopg2
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QComboBox
from PyQt6.uic import loadUi
from user_system import UserSystem, ViewUsersWindow
from connections import MaterTable, MaterTableView, MerchantTable
from database import Database

db = Database()



class MenuWindow(QMainWindow):
    def __init__(self, username: str = None, login_window: QMainWindow = None):
        """
        Initialize the main menu window.

        Args:
            username: The username of the logged-in user
            login_window: Reference to the login window for proper window management
        """
        super().__init__()
        self.add_product_window = None
        try:
            loadUi('ui/MelodiaWindow.ui', self)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load UI: {str(e)}')
            raise
        self.username = username
        self.login_window = login_window
        self.action_users.setEnabled(False)
        self.action_register.setEnabled(False)
        self.action_logout.triggered.connect(self.logout)
        self.action_register.triggered.connect(self.show_registration)
        self.action_product.triggered.connect(self.show_add_products)
        self.view_mater.triggered.connect(self.show_mater)
        self.action_users.triggered.connect(self.show_user_management)
        self.merchant_button.clicked.connect(self.show_merchant)

    def show_user_management(self):
        try:
            if not hasattr(self, 'user_management_window'):
                self.user_management_window = ViewUsersWindow()
            self.user_management_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot open user management: {str(e)}")

    def show_mater(self):
        self.mater_table_window = MaterTableView()
        self.mater_table_window.show()

    def show_registration(self):
        """Show the registration window"""
        self.registration_window = UserRegistration()
        self.registration_window.show()

    def show_add_products(self):
        self.add_product_window = MaterTable()
        self.add_product_window.show()

    def show_merchant(self):
        self.merchant_table_view = MerchantTable()
        self.merchant_table_view.showMaximized()
        self.merchant_table_view.show()

    def logout(self) -> None:
        """Handle logout process by showing login window and closing this window."""
        if self.login_window:
            self.login_window.show()
        self.close()

class UserRegistration(QWidget):
    def __init__(self):
        super(UserRegistration, self).__init__()
        loadUi('ui/registration.ui', self)
        self.registration_button.clicked.connect(self.register_user)
        self.user_db = UserSystem()


    def _hash_password(self, password):
        """Hash a password for storage"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def _check_password(self, password, hashed_password):
        """Check if password matches the hash"""
        try:
            return bcrypt.checkpw(password.encode(), hashed_password)
        except:
            return False

    def register_user(self):
        username = self.username.text()
        password = self.password.text()
        email = self.email.text()
        phone = self.phone.text()
        position = self.position.currentText()

        db.connect()


        if not all([username, password, email, phone, position]):
            QMessageBox.warning(self, 'რეგისტრაციის შეცდომა', 'ყველა ველი უნდა შეივსოს')
            return False

        try:
            hashed_pw = self._hash_password(password)

            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users 
                        (username, password, email, phone, position) 
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (username, hashed_pw.decode(), email, phone, position)
                    )
                    conn.commit()

            QMessageBox.information(self, 'მომხმარებლის დამატება.', 'ახალი მომხმარებელი წარმატებით დაემატა.')
            return True

        except psycopg2.IntegrityError as e:
            print(f"Registration failed: {e} (Username/email/phone might already exist)")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False