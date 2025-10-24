# from PyQt6.QtWidgets import QDialog, QMessageBox
# from PyQt6.uic import loadUi
# from database import Database
# db = Database()
#
#
# class CodeGeneric(QDialog):
#     def __init__(self):
#         super().__init__(parent=None)
#         loadUi('ui/generic.ui', self)
#         self.setWindowTitle('ჯენერიკით ძიება')
#
#     def load_data(self):
#         names = []
#         conn = None
#         # FIX 1: Strip the target product name once to remove extra spaces.
#         product_name = '5-ნოკი  0.05გ #50ტ                                          '.strip()
#         target_generic_code = ''
#
#         try:
#             # Step 1: Attempt to Connect
#             print("Attempting to connect to the database...")
#             conn = db.connect()
#
#             if conn is None:
#                 print("Connection returned None. Check database credentials/server status.")
#                 print("Error: ვერ მოხერხდა მონაცემთა ბაზასთან დაკავშირება.")
#                 return []
#
#             print("Database connection successful.")
#
#             # Step 2: Execute Query and Fetch All Data
#             with conn.cursor() as cursor:
#                 print("Executing SQL query...")
#                 cursor.execute("""
#              SELECT
#                     m."NAM_MAT",          -- 0: პროდუქტის სახელი (Product Name)
#                     n."PRICE",            -- 1: პროდუქტის ღირებულება (Price)
#                     m."ATT_MAT",          -- 2: ATT_MAT string (used to get დღგ/რეცეპტით)
#                     n."DAT_GOOD",         -- 3: ვარგისია
#                     n."NAST",             -- 4: ნაშთი (Stock)
#                     n."SER_NUM",          -- 5: სერიული ნომერი
#                     m."COD_GEN"           -- 6: ჯენერიკ-კოდი (Generic Code)
#                 FROM
#                     public.mater1 AS m
#                 JOIN
#                     public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
#                     """)
#
#                 raw_data = cursor.fetchall()
#                 print(f"Successfully fetched {len(raw_data)} rows.")
#
#             # --- Step 3: FIX - Separate Logic into Two Passes ---
#
#             # 3a. First Pass: Find the generic code (COD_GEN) for the target product
#             for row_data in raw_data:
#                 db_name = row_data[0].strip()  # Strip whitespace from DB name
#
#                 if db_name == product_name:
#                     target_generic_code = row_data[6]
#                     break  # Found the code, exit the loop
#
#             if target_generic_code == '':
#                 print(f"Error: Target product '{product_name}' not found in the database.")
#                 return []
#
#             print(f"Target product's generic code found: {target_generic_code}")
#
#             # 3b. Second Pass: Find all product names sharing that generic code
#             for row_data in raw_data:
#                 current_generic_code = row_data[6]
#                 if current_generic_code == target_generic_code:
#                     # Append the related product name (stripped for cleanliness)
#                     names.append(row_data)
#
#             return names
#
#
#         except Exception as e:
#             # This catches high-level Python/DBAPI errors
#             print("Error:", f"Failed to load data:\n{str(e)}")
#             return []
#
#         finally:
#             # Ensure the connection is explicitly closed
#             if conn:
#                 print("Closing database connection.")
#                 conn.close()
# #
# #     def load_data(self):
# #         try:
# #             with db.connect() as conn:
# #                 with conn.cursor() as cursor:
# #                     cursor.execute("""
# #                  SELECT
# #                         m."NAM_MAT",          -- 0: პროდუქტის სახელი (Product Name)
# #                         n."PRICE",            -- 1: პროდუქტის ღირებულება (Price)
# #                         m."ATT_MAT",          -- 2: ATT_MAT string (used to get დღგ/რეცეპტით)
# #                         n."DAT_GOOD",         -- 3: ვარგისია
# #                         n."NAST",             -- 4: ნაშთი (Stock)
# #                         n."SER_NUM",          -- 5: სერიული ნომერი
# #                         m."COD_GEN"           -- 6: ჯენერიკ-კოდი
# #                     FROM
# #                         public.mater1 AS m
# #                     JOIN
# #                         public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
# #                         """)
# #
# #                 raw_data = cursor.fetchall()
# #                 product_name = '5-ნიტროქსი 0.05გ #80ტ'
# #                 generic_list = []
# #                 for row_data in raw_data:
# #                     name_string = row_data[0]
# #                     generic_list.append(str(name_string))
# #                 return generic_list
# #
# #
# #         except Exception as e:
# #             QMessageBox.critical(self, "Error",
# #                                  f"Failed to load data:\n{str(e)}")
# #
# #
# # vasdv = CodeGeneric()
# #
# # print(vasdv.load_data())
#
#
# # from database import Database
# #
# # db = Database()
# #
# #
# # def load_data():
# #     generic = ''
# #     names = []
# #     conn = None
# #
# #     try:
# #         # Step 1: Attempt to Connect
# #         print("Attempting to connect to the database...")
# #         conn = db.connect()
# #
# #         if conn is None:
# #             print("Connection returned None. Check database credentials/server status.")
# #             print("Error: ვერ მოხერხდა მონაცემთა ბაზასთან დაკავშირება.")
# #             return []
# #
# #         print("Database connection successful.")
# #
# #         # Step 2: Execute Query and Fetch Data (FIX APPLIED HERE)
# #         # The cursor is only defined and open within this 'with' block.
# #         with conn.cursor() as cursor:
# #             print("Executing SQL query...")
# #             cursor.execute("""
# #          SELECT
# #                 m."NAM_MAT",          -- 0: პროდუქტის სახელი (Product Name)
# #                 n."PRICE",            -- 1: პროდუქტის ღირებულება (Price)
# #                 m."ATT_MAT",          -- 2: ATT_MAT string (used to get დღგ/რეცეპტით)
# #                 n."DAT_GOOD",         -- 3: ვარგისია
# #                 n."NAST",             -- 4: ნაშთი (Stock)
# #                 n."SER_NUM",          -- 5: სერიული ნომერი
# #                 m."COD_GEN"           -- 6: ჯენერიკ-კოდი
# #             FROM
# #                 public.mater1 AS m
# #             JOIN
# #                 public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
# #                 """)
# #
# #             # Fetch the data *before* the 'with' block exits and closes the cursor
# #             raw_data = cursor.fetchall()
# #             print(f"Successfully fetched {len(raw_data)} rows.")
# #             product_name = '5-ნოკი  0.05გ #50ტ                                          '
# #         # Step 3: Process data (using the fetched raw_data list)
# #             for row_data in raw_data:
# #                 name_string = row_data[0]
# #                 if name_string == product_name:
# #                     generic = str(row_data[6])
# #                 generics = row_data[6]
# #                 if generics == generic:
# #                     names.append(name_string)
# #             return names
# #
# #
# #
# #
# #     except Exception as e:
# #         # This catches high-level Python/DBAPI errors
# #         print("Error:", f"Failed to load data:\n{str(e)}")
# #         return []
# #
# #     finally:
# #         # Ensure the connection is explicitly closed if it was opened
# #         if conn:
# #             print("Closing database connection.")
# #             conn.close()
# #
# #
# # # Call the function
# # results = load_data()
# # print("\n--- Final Results (Product Names) ---")
# # print(results)
#
#
# from database import Database
#
# db = Database()
#
#
# def load_data():
#     names = []
#     conn = None
#     # FIX 1: Strip the target product name once to remove extra spaces.
#     product_name = '5-ნოკი  0.05გ #50ტ                                          '.strip()
#     target_generic_code = ''
#
#     try:
#         # Step 1: Attempt to Connect
#         print("Attempting to connect to the database...")
#         conn = db.connect()
#
#         if conn is None:
#             print("Connection returned None. Check database credentials/server status.")
#             print("Error: ვერ მოხერხდა მონაცემთა ბაზასთან დაკავშირება.")
#             return []
#
#         print("Database connection successful.")
#
#         # Step 2: Execute Query and Fetch All Data
#         with conn.cursor() as cursor:
#             print("Executing SQL query...")
#             cursor.execute("""
#          SELECT
#                 m."NAM_MAT",          -- 0: პროდუქტის სახელი (Product Name)
#                 n."PRICE",            -- 1: პროდუქტის ღირებულება (Price)
#                 m."ATT_MAT",          -- 2: ATT_MAT string (used to get დღგ/რეცეპტით)
#                 n."DAT_GOOD",         -- 3: ვარგისია
#                 n."NAST",             -- 4: ნაშთი (Stock)
#                 n."SER_NUM",          -- 5: სერიული ნომერი
#                 m."COD_GEN"           -- 6: ჯენერიკ-კოდი (Generic Code)
#             FROM
#                 public.mater1 AS m
#             JOIN
#                 public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
#                 """)
#
#             raw_data = cursor.fetchall()
#             print(f"Successfully fetched {len(raw_data)} rows.")
#
#         # --- Step 3: FIX - Separate Logic into Two Passes ---
#
#         # 3a. First Pass: Find the generic code (COD_GEN) for the target product
#         for row_data in raw_data:
#             db_name = row_data[0].strip()  # Strip whitespace from DB name
#
#             if db_name == product_name:
#                 target_generic_code = row_data[6]
#                 break  # Found the code, exit the loop
#
#         if target_generic_code == '':
#             print(f"Error: Target product '{product_name}' not found in the database.")
#             return []
#
#         print(f"Target product's generic code found: {target_generic_code}")
#
#         # 3b. Second Pass: Find all product names sharing that generic code
#         for row_data in raw_data:
#             current_generic_code = row_data[6]
#             if current_generic_code == target_generic_code:
#                 # Append the related product name (stripped for cleanliness)
#                 names.append(row_data)
#
#         return names
#
#
#     except Exception as e:
#         # This catches high-level Python/DBAPI errors
#         print("Error:", f"Failed to load data:\n{str(e)}")
#         return []
#
#     finally:
#         # Ensure the connection is explicitly closed
#         if conn:
#             print("Closing database connection.")
#             conn.close()
#
#
# # Call the function
# results = load_data()
# print("\n--- Final Results (Product Names) ---")
# print(results)

from PyQt6.QtWidgets import QDialog, QMessageBox, QTableView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSignal, QModelIndex, Qt
from typing import List

# Assume database.py is correctly configured
from database import Database

db = Database()


class CodeGeneric(QDialog):
    # Signal to emit the selected row's data (list of strings for all columns)
    product_selected_for_basket = pyqtSignal(list)

    def __init__(self, selected_product_name: str, parent=None):
        super().__init__(parent)
        loadUi('ui/generic.ui', self)

        # Access the QTableView named 'generic_list'
        self.generic_table_view = self.findChild(QTableView, 'generic_list')

        # Setup the model
        self.model = QStandardItemModel()
        if self.generic_table_view:
            self.generic_table_view.setModel(self.model)
            self.generic_table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

            # Connect double-click action
            self.generic_table_view.doubleClicked.connect(self.add_to_basket_from_selection)

        # Search context
        self.product_name = selected_product_name.strip()
        self.setWindowTitle(f'ჯენერიკით ძიება - {self.product_name}')

        self.load_data()

    def load_data(self):
        raw_data = []
        target_generic_code = None
        self.model.clear()

        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                     SELECT
                            m."NAM_MAT",          -- 0: Product Name
                            n."PRICE",            -- 1: Price
                            m."ATT_MAT",          -- 2: ATT_MAT string
                            n."DAT_GOOD",         -- 3: Expiration Date
                            n."NAST",             -- 4: Stock
                            n."SER_NUM",          -- 5: Serial Number
                            m."COD_GEN"           -- 6: Generic Code
                        FROM
                            public.mater1 AS m
                        JOIN
                            public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
                        """)

                    raw_data = cursor.fetchall()

            # 2a. First Pass: Find the generic code
            for row_data in raw_data:
                if row_data[0].strip() == self.product_name:
                    target_generic_code = row_data[6]
                    break

            if target_generic_code is None:
                QMessageBox.warning(self, "Warning", f"ჯენერიკ კოდი პროდუქტისთვის '{self.product_name}' ვერ მოიძებნა.")
                return

            self.setWindowTitle(f'ჯენერიკით ძიება - კოდი: {target_generic_code}')

            # 2b. Second Pass: Filter the rows that share the generic code
            generic_product_rows = []
            for row_data in raw_data:
                if row_data[6] == target_generic_code:
                    generic_product_rows.append(row_data)

            # Step 3: Display Results
            self.display_generic_data(generic_product_rows)

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"ჯენერიკული მონაცემების ჩატვირთვა ვერ მოხერხდა:\n{str(e)}")

    def display_generic_data(self, data: List[tuple]):
        """Populates the QStandardItemModel with the filtered generic data and sets headers."""

        headers = [
            'პროდუქტის სახელი', 'ღირებულება', 'ატრიბუტები', 'ვარგისია',
            'ნაშთი', 'სერიული ნომერი', 'ჯენერიკ-კოდი'
        ]
        self.model.setHorizontalHeaderLabels(headers)

        if not data:
            QMessageBox.information(self, "Info", "ამ ჯენერიკ კოდით სხვა პროდუქტი ვერ მოიძებნა.")
            return

        # Insert data row by row
        for row_data in data:
            row_items = [QStandardItem(str(cell_data).strip()) for cell_data in row_data]
            self.model.appendRow(row_items)

        # Adjust view settings
        if self.generic_table_view:
            self.generic_table_view.resizeColumnsToContents()
            header = self.generic_table_view.horizontalHeader()
            header.setSectionResizeMode(0, header.ResizeMode.Stretch)

    def add_to_basket_from_selection(self, index: QModelIndex):
        """
        1. Extracts the full row data from the model based on the selected index.
        2. Emits the signal containing the data.
        """

        # Ensure a valid index is selected
        if not index.isValid():
            QMessageBox.warning(self, "Warning", "გთხოვთ, აირჩიეთ პროდუქტი.")
            return

        row = index.row()
        row_data = []

        # Extract data from all columns of the selected row
        num_columns = self.model.columnCount()

        for col in range(num_columns):
            item = self.model.item(row, col)
            # Append the raw text data from the model item
            row_data.append(item.text() if item else '')

        if row_data:
            # Emit the signal with the selected product's data
            self.product_selected_for_basket.emit(row_data)

            # Close the dialog
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "მონაცემები ვერ მოიძებნა ამ რიგისთვის.")

    def keyPressEvent(self, event):
        """Handle Enter key press to trigger basket addition."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Get the currently selected index
            selected_indexes = self.generic_table_view.selectionModel().selectedIndexes()
            if selected_indexes:
                # Use the first index to call the selection handler
                self.add_to_basket_from_selection(selected_indexes[0])
                return

                # Pass other key events up to the base class
        super().keyPressEvent(event)
