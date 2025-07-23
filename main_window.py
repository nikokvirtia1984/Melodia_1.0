# from PyQt6.QtGui.QTextCursor import position
from PyQt6.QtCore import QFile, QIODevice, QTextStream
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox,QLabel, QWidget
from PyQt6.uic import loadUi
import sys
from main_menu import MenuWindow
from user_system import UserSystem, RecoverPass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('ui/LoginWindow.ui', self)
        self.load_qss('ui/Adaptic.qss')
        self.user_system = UserSystem()
        self.main_menu = None
        # Connect signals
        self.login_button.clicked.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        self.pass_restore.setOpenExternalLinks(False)
        self.pass_restore.linkActivated.connect(self.show_password_form)
        self.password_form = RecoverPass()


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
                self.main_menu.setWindowTitle(f"მელოდია - {username} ({position})")
                # Set permissions based on position
                if position == "ადმინისტრატორი":
                    self.main_menu.action_users.setEnabled(True)
                    self.main_menu.action_register.setEnabled(True)
                self.main_menu.show()
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