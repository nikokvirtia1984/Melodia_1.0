from email.mime.text import MIMEText
import psycopg2
import random
import smtplib
import bcrypt
from getpass import getpass  # For secure password input
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.uic import loadUi


class UserSystem:
    def __init__(self):
        self._initialize_db()

    def _get_connection(self):
        """Establish and return a database connection"""
        return psycopg2.connect(
            host="localhost",
            dbname="postgres",
            user="postgres",
            password="Eleneliza1984",
            port=5432
        )

    def _initialize_db(self):
        """Initialize the database table"""
        try:
            with self._get_connection() as conn:
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


    def login(self, username, password):
        """Authenticate a user"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT password FROM users 
                        WHERE username = %s
                        """,
                        (username,)
                    )
                    result = cursor.fetchone()

                    if result and self._check_password(password, result[0].encode()):
                        print("Login successful!")
                        return True

            print("Invalid username or password")
            return False

        except Exception as e:
            print(f"Login error: {e}")
            return False
    # def _hash_password(self, password: str) -> bytes:
    #     salt = bcrypt.gensalt()
    #     return bcrypt.hashpw(password.encode('utf-8'), salt)
    #
    # def login(self, username: str, password: str) -> bool:
    #     """
    #     Authenticate a user
    #
    #     Args:
    #         username: The username to check
    #         password: The plaintext password to verify
    #
    #     Returns:
    #         bool: True if login successful, False otherwise
    #     """
    #     try:
    #         with self._get_connection() as conn:
    #             with conn.cursor() as cursor:
    #                 # Get the stored password hash
    #                 cursor.execute('''
    #                     SELECT password FROM users WHERE username = %s
    #                 ''', (username,))
    #
    #                 result = cursor.fetchone()
    #
    #                 if not result:
    #                     return False
    #
    #                 stored_hash = result[0]
    #                 input_hash = self._hash_password(password)
    #
    #                 return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    #
    #     except psycopg2.Error as e:
    #         print(f"Database error during login: {e}")
    #         return False



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

    def check_email_and_send_code(self):
        email = self.email.text().strip()

        if not email:
            QMessageBox.warning(self, "Error", "Please enter an email address")
            return

        try:
            # Check email in PostgreSQL
            conn = psycopg2.connect(
                host="localhost",
                dbname="postgres",
                user="postgres",
                password="Eleneliza1984",
                port=5432
            )
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM users WHERE email = %s)", (email,))
            email_exists = cursor.fetchone()[0]

            if email_exists:
                # Generate and send verification code
                verification_code = self.generate_verification_code()
                self.send_verification_email(email, verification_code)

                # Store the code for verification
                self.verification_codes[email] = verification_code

                QMessageBox.information(self, "Code Sent",
                                        f"A 4-digit verification code has been sent to {email}")
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
        msg = MIMEText(f"Your verification code is: {code}\n\nThis code will expire in 10 minutes.")
        msg['Subject'] = 'Password Reset Verification Code'
        msg['From'] = self.smtp_config['sender_email']
        msg['To'] = recipient_email

        with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
            server.starttls()
            server.login(self.smtp_config['sender_email'], self.smtp_config['password'])
            server.sendmail(self.smtp_config['sender_email'], recipient_email, msg.as_string())

    def show_password_form(self, link="#"):
        """Show the password reset form after code verification"""
        self.password_form = loadUi('ui/password_restore.ui')
        self.password_form.code_verify_button.clicked.connect(self.verify_code)
        self.password_form.show()

    def verify_code(self):
        """Verify the entered code matches the sent code"""
        email = self.email.text().strip()
        entered_code = self.password_form.code_input.text().strip()

        if email in self.verification_codes:
            if entered_code == self.verification_codes[email]:
                QMessageBox.information(self, "Success", "Code verified! You can now reset your password.")
                # Proceed with password reset logic
            else:
                QMessageBox.warning(self, "Invalid Code", "The verification code is incorrect.")
        else:
            QMessageBox.warning(self, "Error", "No verification code found for this email.")
