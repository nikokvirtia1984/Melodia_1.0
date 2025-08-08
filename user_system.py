from PyQt6.QtWidgets import QWidget, QMessageBox, QTableView, QHeaderView, QVBoxLayout
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.uic import loadUi
import psycopg2
from contextlib import contextmanager
from typing import List
import time
from email.mime.text import MIMEText
import psycopg2
import random
import smtplib
import bcrypt
import logging
import os
from getpass import getpass  # For secure password input

from database import Database

from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QWidget, QMessageBox, QTableView, QHeaderView, QPushButton
from PyQt6.uic import loadUi

db = Database()


class UserSystem:
    def __init__(self):
        self._initialize_db()
    #
    # def _get_connection(self):
    #     """Establish and return a database connection"""
    #     return psycopg2.connect(
    #         host="localhost",
    #         dbname="melodia",
    #         user="melodia",
    #         password="melo",
    #         port=5432
    #     )

    def _initialize_db(self):
        """Initialize the database table"""
        try:
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
        except psycopg2.Error as e:
            print(f"Database initialization error: {e}")

    def _hash_password(self, password):
        """Hash a password for storage"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def _check_password(self, password, hashed_password):
        """Check if password matches the hash"""
        try:
            return bcrypt.checkpw(password.encode(), hashed_password)
        except:
            return False

    def login(self, username, password, parent_widget=None):
        """Authenticate a user and return their position if successful

        Args:
            username: The username to authenticate
            password: The password to verify
            parent_widget: Optional parent widget for message boxes

        Returns:
            tuple: (success: bool, position: str)
                   or (False, None) if login fails
        """
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT password, position FROM users 
                        WHERE username = %s
                        """,
                        (username,)
                    )
                    result = cursor.fetchone()

                    if result:
                        stored_password, position = result
                        if self._check_password(password, stored_password.encode()):
                            print("Login successful!")
                            return True, position
                        else:
                            QMessageBox.warning(parent_widget,
                                                "Login Failed",
                                                "Incorrect password")
                    else:
                        QMessageBox.warning(parent_widget,
                                            "Login Failed",
                                            "User not found")

                    return False, None

        except Exception as e:
            QMessageBox.critical(parent_widget,
                                 "Database Error",
                                 f"Login failed: {str(e)}")
            return False, None



class RecoverPass(QWidget):
    def __init__(self):
        super().__init__()
        loadUi('ui/code_send.ui', self)
        # self.pass_restore.setOpenExternalLinks(False)
        # self.pass_restore.linkActivated.connect(self.show_password_form)
        self.code_Button.clicked.connect(self.check_email_and_send_code)


        # Store verification codes temporarily
        self.verification_codes = {}  # {email: code}

        # Email configuration (replace with your SMTP details)
        self.smtp_config = {
            'server': 'smtp.gmail.com',  # Example for Gmail
            'port': 587,
            'sender_email': 'nkvirtia@gmail.com',
            'password': 'wstq dqqw skpz ajyd'  # Use app-specific password
        }

    def _hash_password(self, password):
        """Hash a password for storage"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def _check_password(self, password, hashed_password):
        """Check if password matches the hash"""
        try:
            return bcrypt.checkpw(password.encode(), hashed_password)
        except:
            return False

    def check_email_and_send_code(self):
        email = self.email.text().strip()
        self.current_email = email

        if not email:
            QMessageBox.warning(self, "Error", "Please enter an email address")
            return

        try:
            # Check email in PostgreSQL
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM users WHERE email = %s)", (email,))
            email_exists = cursor.fetchone()[0]

            if email_exists:
                # Generate and send verification code
                verification_code = self.generate_verification_code()
                self.send_verification_email(email, verification_code)

                # Store the code for verification
                self.verification_codes[email] = (verification_code, time.time())

                QMessageBox.information(self, "Code Sent",
                                        f"A 4-digit verification code has been sent to {email}")
                self.close()
                self.show_password_form()  # Show the code verification form
            else:
                QMessageBox.warning(self, "Not Found",
                                    "This email is not registered in our system.")

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not check email: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Email Error", f"Failed to send email: {str(e)}")
        finally:
            if 'conn' in locals():
                conn.close()

    def generate_verification_code(self):
        """Generate a random 4-digit code"""
        return str(random.randint(1000, 9999))

    def send_verification_email(self, recipient_email, code):
        """Send email with verification code using SMTP"""
        msg = MIMEText(f"Your verification code is: {code}\n\nThis code will expire in 5 minutes.")
        msg['Subject'] = 'Password Reset Verification Code'
        msg['From'] = self.smtp_config['sender_email']
        msg['To'] = recipient_email

        with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
            server.starttls()
            server.login(self.smtp_config['sender_email'], self.smtp_config['password'])
            server.sendmail(self.smtp_config['sender_email'], recipient_email, msg.as_string())

    def show_password_form(self, link="#"):
        """Show the password reset form after code verification"""
        self.password_restore = loadUi('ui/password_restore.ui')
        self.password_restore.verify_button.clicked.connect(self.verify_code)
        self.password_restore.restore_pass.clicked.connect(self.reset_password)
        self.password_restore.restore_pass.setEnabled(False)
        self.password_restore.new_pass.setEnabled(False)
        self.password_restore.repeat_pass.setEnabled(False)
        self.password_restore.show()

    def verify_code(self):
        """Verify the entered code matches the sent code"""
        if not hasattr(self, 'current_email') or not self.current_email:
            QMessageBox.warning(self, "Error", "No email associated with this request")
            return

        email = self.current_email
        entered_code = self.password_restore.code_line.text().strip()

        # Check if email exists in verification codes
        if email not in self.verification_codes:
            QMessageBox.warning(self, "Error", "No verification code found for this email.")
            return

        # Get stored code and timestamp
        stored_code, timestamp = self.verification_codes[email]

        # Check if code is expired (5 minutes = 300 seconds)
        if time.time() - timestamp >300:
            QMessageBox.warning(self, "Expired",
                                "The verification code has expired (5 minutes). Please request a new one.")
            # Optional: Remove the expired code
            del self.verification_codes[email]
            return

        # Verify the code
        if entered_code == stored_code:
            QMessageBox.information(self, "Success", "Code verified! You can now reset your password.")
            self.password_restore.restore_pass.setEnabled(True)
            self.password_restore.new_pass.setEnabled(True)
            self.password_restore.repeat_pass.setEnabled(True)
        else:
            QMessageBox.warning(self, "Invalid Code", "The verification code is incorrect.")


    def reset_password(self):
        """Handle password reset after successful verification"""
        new_pass = self.password_restore.new_pass.text()
        repeat_pass = self.password_restore.repeat_pass.text()
        if not new_pass or not repeat_pass:
            QMessageBox.warning(self, 'შეცდომა', 'გთხოვთ შეიყვანოთ და დაადასტუროთ ახალი პაროლი.')
            return
        if new_pass != repeat_pass:
            QMessageBox.warning(self, 'შეცდომა', 'პაროლები არ ემთხვევა.')

        try:
            hash_pass = self._hash_password(new_pass)
            conn = db.connect()
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hash_pass.decode(), self.current_email))
            QMessageBox.information(self, 'წარმატებული', 'პაროლი წარმატებით შეიცვალა.')
            self.password_restore.close()
            self.close()
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not update password: {str(e)}")
        finally:
            if conn in locals():
                conn.close()



class ViewUsersWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel()
        loadUi('ui/view_users.ui', self)
        self.load_data()

        self.tableView.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableView.hideColumn(0)
        self.btn_refresh.clicked.connect(self.save_changes)
        self.btn_delete.clicked.connect(self.delete_selected)

    # def get_db_connection(self):
    #     """Establish database connection with error handling"""
    #     try:
    #         return db.connect()
    #     except Exception as e:
    #         QMessageBox.critical(self, "Database Error",
    #                              f"Connection failed: {str(e)}")
    #         raise

    def load_data(self):

        """Load and display user data with proper formatting"""
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT ID, username, email,
                               COALESCE(phone, 'N/A') as phone,
                               position,
                               to_char(created_at, 'YYYY-MM-DD HH24:MI') as created_at
                        FROM users
                        ORDER BY created_at DESC
                    """)
                    self.display_users(cursor.fetchall())

        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to load data:\n{str(e)}")

    def display_users(self, users: List[tuple]):
        """Populate table with user data"""
        self.model.setHorizontalHeaderLabels(
            ["ID", "Username", "Email", "Phone", "Position", "Created At"]
        )

        for user in users:
            row = [QStandardItem(str(item)) for item in user]

            # Make ID and creation date non-editable
            row[5].setEditable(False)  # Created At
            # Truncate long email addresses for display
            if len(row[2].text()) > 20:
                row[2].setText(row[2].text()[:17] + "...")

            self.model.appendRow(row)

        self.tableView.setModel(self.model)

    def save_changes(self):

        """Save all edited data to the database"""
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    for row in range(self.model.rowCount()):
                        user_id = int(self.model.item(row, 0).text())
                        username = self.model.item(row, 1).text()
                        email = self.model.item(row, 2).text()
                        phone = self.model.item(row, 3).text()
                        position = self.model.item(row, 4).text()

                        # Skip if phone was originally N/A (NULL)
                        phone_value = None if phone == "N/A" else phone

                        cursor.execute("""
                            UPDATE users SET
                                username = %s,
                                email = %s,
                                phone = %s,
                                position = %s
                            WHERE id = %s
                        """, (username, email, phone_value, position, user_id))

                    conn.commit()
                    QMessageBox.information(self, "Success", "Changes saved successfully")

            self.model.clear()

            self.load_data() # Refresh to show saved changes
            self.tableView.hideColumn(0)

        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to save changes:\n{str(e)}")


    def delete_selected(self):
        """Delete selected users with proper type handling"""
        selected = self.tableView.selectionModel().selectedRows(0)
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select users to delete")
            return

        try:
            # Get IDs as integers
            ids = [int(self.tableView.model().itemFromIndex(index).text())
                   for index in selected]

            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete {len(ids)} selected user(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                with db.connect() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM users WHERE id = ANY(%s)",
                            (ids,)
                        )
                    conn.commit()
                self.model.clear()
                self.load_data()  # Refresh data
                self.tableView.hideColumn(0)
                QMessageBox.information(self, "Success", "Users deleted successfully")

        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid ID format")
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 f"Failed to delete users:\n{str(e)}")

    def closeEvent(self, event):
        """Clean up resources"""
        event.accept()