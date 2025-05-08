import psycopg2
import bcrypt
from getpass import getpass  # For secure password input


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
                            position VARCHAR(100),
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

    def register_user(self):
        """Register a new user"""
        print("\n--- User Registration ---")
        username = input('Enter username: ').strip()
        password = input('Enter password: ').strip()  # Hidden input
        email = input('Enter email: ').strip()
        phone = input('Enter phone number: ').strip()
        position = input('Enter position: ').strip()

        if not all([username, password, email, phone, position]):
            print("Error: All fields are required")
            return False

        try:
            hashed_pw = self._hash_password(password)

            with self._get_connection() as conn:
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

            print("User registered successfully!")
            return True

        except psycopg2.IntegrityError as e:
            print(f"Registration failed: {e} (Username/email/phone might already exist)")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
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