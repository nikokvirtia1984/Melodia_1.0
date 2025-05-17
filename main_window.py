from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox,QLabel, QWidget
from PyQt6.uic import loadUi
import sys
from main_menu import MenuWindow
from user_system import UserSystem, RecoverPass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('ui/LoginWindow.ui', self)

        self.user_system = UserSystem()
        self.main_menu = None
        # Connect signals
        self.login_button.clicked.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        self.pass_restore.setOpenExternalLinks(False)
        self.pass_restore.linkActivated.connect(self.show_password_form)
        self.password_form = RecoverPass()


    def show_password_form(self):
        self.password_form.show()


    def handle_login(self):
        """Handle login process"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, 'Input Error', 'Please enter both username and password')
            return

        try:
            if self.user_system.login(username, password):
                self.main_menu = MenuWindow(username=username, login_window=self)
                self.main_menu.setWindowTitle(f"მელოდია-{username}")
                self.main_menu.show()
                self.hide()  # Hide login window
            else:
                QMessageBox.warning(self, 'Login Failed', 'Invalid username or password')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Login failed: {str(e)}')

    def handle_registration(self):
        pass


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