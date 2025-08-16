import sys
import psycopg2
from PyQt6.QtWidgets import QMessageBox, QApplication

class Database:
    def __init__(self):
        pass

    def connect(self):
        try:
            return psycopg2.connect(
                host="localhost",
                dbname="melodia",
                user="melodia",
                password="melodia",
                port=5432
            )
        except Exception as e:
            app = QApplication(sys.argv)
            msgbox = QMessageBox()
            msgbox.setWindowTitle("კავშირის შეცდომა")
            msgbox.setText("მონაცემთა ბაზასთან დაკავშირება ვერ მოხერხდა,"
                           "\nგადაამოწმეთ ინტერნეთან კავშირი ან სცადეთ მოგვიანებით")
            msgbox.exec()

            sys.exit(1)