# from typing import List
# from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
# from PyQt6.QtGui import QStandardItemModel, QStandardItem
# from PyQt6.QtWidgets import QWidget, QMessageBox, QTableView, QHeaderView
# from PyQt6.uic import loadUi
# import os
# import logging
# import pdfkit
# import jinja2
# import datetime
#
# from database import Database
#
# db = Database()
#
#
#
# class ReturnProduct(QWidget):
#     # --- 1. DEFINE CUSTOM SIGNAL ---
#     product_returned = pyqtSignal()
#     # -------------------------------
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         loadUi("ui/return.ui", self)
#         self.sourceModel = QStandardItemModel()
#         self.checkouts.setModel(self.sourceModel)
#
#         # Configure the table view
#         self.checkouts.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
#
#         # Connect the buttons
#         self.return_button.clicked.connect(self.product_return)
#         self.print_button.clicked.connect(self.invoice_print)
#
#         # Load the data from the database
#         self.load_data()
#         self.code_filter.textChanged.connect(self.filter_item_with_code)
#         self.date_filter.textChanged.connect(self.filter_item_with_date)
#
#
#     def load_merchant_data(self):
#         try:
#             with db.connect() as conn:
#                 with conn.cursor() as cursor:
#                     cursor.execute("""
#                     SELECT
#                         m."NAM_MAT",          -- 0: პროდუქტის სახელი (Product Name)
#                         n."PRICE",            -- 1: პროდუქტის ღირებულება (Price)
#                         n."COD_MAT",          -- 2: დღ/სპ
#                         n."DAT_GOOD",         -- 3: ვარგისია
#                         n."NAST",             -- 4: ნაშთი (Stock)
#                         n."SER_NUM"           -- 5: სერიული ნომერი
#                     FROM
#                         public.mater1 AS m
#                     JOIN
#                         public.nashti AS n ON m."COD_MAT" = n."COD_MAT";
#                     """)
#                     column_names = [desc[0] for desc in cursor.description]
#                     self.display_source_data(cursor.fetchall(), column_names)
#         except Exception as e:
#             QMessageBox.critical(self, "Error",
#                                  f"Failed to load data:\n{str(e)}")
#
#     def load_data(self):
#         try:
#             with db.connect() as conn:
#                 with conn.cursor() as cursor:
#                     cursor.execute("""
#                     SELECT
#                         o."invoice_id",
#                         o."product_name",
#                         o."quantity",
#                         o."item_quantity",
#                         o."price",
#                         i."total_price",
#                         i."username",
#                         to_char(i."created_at", 'YYYY-MM-DD HH24:MI')
#                     FROM
#                         public.invoices AS i
#                     JOIN
#                         public.operations AS o ON i."invoice_id" = o."invoice_id";
#                     """)
#                     self.display_source_data(cursor.fetchall())
#         except Exception as e:
#             QMessageBox.critical(self, "Error",
#                                  f"Failed to load data:\n{str(e)}")
#
#     def display_source_data(self, data: List[tuple]):
#         self.sourceModel.clear()
#         source_georgian_headers = [
#             'ქვითრის კოდი',
#             'პროდუქტის სახელი',
#             'რაოდენობა',
#             'ერთეულის რაოდენობა',
#             'პროდუქტის ფასი',
#             'მთლიანი ფასი',
#             'ოპერატორი',
#             'თარიღი'
#         ]
#         self.sourceModel.setHorizontalHeaderLabels(source_georgian_headers)
#         if data:
#             self.sourceModel.beginInsertRows(QModelIndex(), 0, len(data) - 1)
#             for row_data in data:
#                 row_items = [QStandardItem(str(cell_data)) for cell_data in row_data]
#                 for i, item in enumerate(row_items):
#                     cell_data = row_data[i]
#                     if i == 0:
#                         item.setToolTip(f"პროდუქტის დასახელება: {cell_data}")
#                     elif i == 5:
#                         item.setToolTip(f"ოპერატორი: {cell_data}")
#                 self.sourceModel.appendRow(row_items)
#             self.sourceModel.endInsertRows()
#         self.checkouts.resizeColumnsToContents()
#         self.checkouts.resizeRowsToContents()
#
#     def product_return(self):
#         """Returns a selected product to the database stock."""
#         selected = self.checkouts.selectionModel().selectedRows()
#         if not selected:
#             QMessageBox.warning(self, "გაფრთხილება", "გთხოვთ, აირჩიეთ დასაბრუნებელი პროდუქტი.")
#             return
#
#         row = selected[0].row()
#         invoice_id = self.sourceModel.item(row, 0).text()
#         product_name = self.sourceModel.item(row, 1).text()
#         quantity = self.sourceModel.item(row, 2).text()
#
#         reply = QMessageBox.question(self, "დაბრუნების დადასტურება",
#                                      f"დარწმუნებული ხართ, რომ გსურთ პროდუქტის დაბრუნება: {product_name}?",
#                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
#
#         if reply == QMessageBox.StandardButton.Yes:
#             try:
#                 with db.connect() as conn:
#                     with conn.cursor() as cursor:
#                         # Find the product's code
#                         cursor.execute(
#                             "SELECT \"COD_MAT\" FROM public.mater1 WHERE \"NAM_MAT\" = %s",
#                             (product_name,)
#                         )
#                         cod_mat = cursor.fetchone()
#
#                         if cod_mat:
#                             # Add the quantity back to the 'nashti' table
#                             cursor.execute(
#                                 """
#                                 UPDATE public.nashti
#                                 SET "NAST" = "NAST" + %s
#                                 WHERE "COD_MAT" = %s
#                                 """,
#                                 (quantity, cod_mat[0])
#                             )
#
#                             # Delete the record from the 'operations' table
#                             cursor.execute(
#                                 """
#                                 DELETE FROM public.operations WHERE "invoice_id" = %s AND "product_name" = %s
#                                 """,
#                                 (invoice_id, product_name)
#                             )
#                             conn.commit()
#                             QMessageBox.information(self, "წარმატება", "პროდუქტი წარმატებით დაბრუნდა.")
#                             self.load_data()
#                             # --- 2. EMIT SIGNAL TO REFRESH MERCHANT TABLE ---
#                             self.product_returned.emit()
#                             # ------------------------------------------------
#
#
#                             # Refresh the table view
#                         else:
#                             QMessageBox.warning(self, "შეცდომა",
#                                               f"პროდუქტი '{product_name}' მონაცემთა ბაზაში ვერ მოიძებნა.")
#
#
#             except Exception as e:
#                 QMessageBox.critical(self, "Database Error", f"პროდუქტის დაბრუნება ვერ მოხერხდა: {e}")
#
#     def invoice_print(self):
#         """Generates and prints the invoice for the selected record."""
#         selected = self.checkouts.selectionModel().selectedRows()
#         if not selected:
#             QMessageBox.warning(self, "გაფრთხილება", "გთხოვთ, აირჩიეთ დასაბეჭდი ქვითარი.")
#             return
#
#         row = selected[0].row()
#         invoice_id = self.sourceModel.item(row, 0).text()
#
#         try:
#             with db.connect() as conn:
#                 with conn.cursor() as cursor:
#                     # Get the main invoice details
#                     cursor.execute(
#                         "SELECT * FROM public.invoices WHERE invoice_id = %s",
#                         (invoice_id,)
#                     )
#                     invoice_record = cursor.fetchone()
#
#                     if not invoice_record:
#                         QMessageBox.warning(self, "შეცდომა", "ქვითარი ვერ მოიძებნა.")
#                         return
#
#                     # Get all items for this invoice
#                     cursor.execute(
#                         "SELECT product_name, quantity, item_quantity, price FROM public.operations WHERE invoice_id = %s",
#                         (invoice_id,)
#                     )
#                     operation_records = cursor.fetchall()
#
#             # Construct the context dictionary for the HTML template
#             invoice_context = {
#                 'invoice_number': invoice_record[0],  # Assuming invoice_id is the first column
#                 'created_date': invoice_record[3].strftime('%Y-%m-%d / %H:%M:%S'),  # Assuming created_at is the 4th
#                 'total_price': f"{invoice_record[2]:.2f}",  # Assuming total_price is the 3rd
#                 'items': [
#                     {'პროდუქტის სახელი': row[0], 'რაოდენობა': row[1], 'ერთეულის რაოდენობა': row[2], 'ფასი': row[3]}
#                     for row in operation_records
#                 ]
#             }
#
#             # Generate and print the PDF
#             template_loader = jinja2.FileSystemLoader('./')
#             template_env = jinja2.Environment(loader=template_loader)
#             template = template_env.get_template('invoice.html')
#             output_text = template.render(invoice_context)
#
#             config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
#             filename = f'Invoice({invoice_record[3].strftime("%Y-%m-%d")})#{invoice_id}.pdf'
#             full_path = os.path.join('invoices', filename)
#
#             # Ensure the invoices directory exists
#             if not os.path.exists('invoices'):
#                 os.makedirs('invoices')
#
#             pdfkit.from_string(output_text, full_path, configuration=config)
#
#             QMessageBox.information(self, 'ინვოისის ამობეჭდვა', 'ინვოისი წარმატებით შეიქმნა! გსურთ ამობეჭდვა?',
#                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
#             os.startfile(full_path)
#         except Exception as e:
#             QMessageBox.critical(self, "PDF Error", f"ინვოისის შექმნა ვერ მოხერხდა: {e}")
#
#     def _apply_filter(self, filter_text, column):
#         """Helper method to apply filtering to a specific column"""
#         for row in range(self.sourceModel.rowCount()):
#             item = self.sourceModel.item(row, column)
#             match = item is not None and filter_text in item.text().lower()
#             self.checkouts.setRowHidden(row, not match)
#
#
#     def filter_item_with_code(self):
#         filter_text = self.code_filter.text().lower()
#         self._apply_filter(filter_text, column=0)
#
#     def filter_item_with_date(self):
#         filter_text = self.date_filter.text().lower()
#         self._apply_filter(filter_text, column=7)
#
#


from typing import List
from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QWidget, QMessageBox, QTableView, QHeaderView
from PyQt6.uic import loadUi
import os
import logging
import pdfkit
import jinja2
import datetime

from database import Database

db = Database()


class ReturnProduct(QWidget):
    # --- 1. DEFINE CUSTOM SIGNAL ---
    product_returned = pyqtSignal()

    # -------------------------------

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("ui/return.ui", self)
        self.sourceModel = QStandardItemModel()
        self.checkouts.setModel(self.sourceModel)

        # Configure the table view
        self.checkouts.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        # Connect the buttons
        self.return_button.clicked.connect(self.product_return)
        self.print_button.clicked.connect(self.invoice_print)

        # Connect Filters
        self.code_filter.textChanged.connect(self.filter_item_with_code)
        self.date_filter.textChanged.connect(self.filter_item_with_date)

        # --- CHECKBOX CONNECTION ---
        # Ensure you named your checkbox 'sold_checkbox' in Qt Designer!
        if hasattr(self, 'sold_checkbox'):
            self.sold_checkbox.stateChanged.connect(self.load_data)
        else:
            logging.warning("sold_checkbox not found in UI file.")

        # Load the data from the database
        self.load_data()

    def load_data(self):
        """
        Loads data based on the 'Sold' status.
        - Checkbox UNCHECKED: Shows SOLD items (sold = TRUE).
        - Checkbox CHECKED: Shows RETURNED/UNSOLD items (sold = FALSE).
        """
        # Determine target status based on checkbox
        if hasattr(self, 'sold_checkbox'):
            target_sold_status = not self.sold_checkbox.isChecked()
        else:
            target_sold_status = True  # Default to showing sold items if checkbox missing

        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                    SELECT 
                        o."invoice_id",
                        o."product_name",
                        o."quantity",
                        o."item_quantity",
                        o."price",
                        i."total_price",
                        i."username",
                        to_char(i."created_at", 'YYYY-MM-DD HH24:MI'),
                        o."sold"
                    FROM
                        public.invoices AS i
                    JOIN
                        public.operations AS o ON i."invoice_id" = o."invoice_id"
                    WHERE
                        o."sold" = %s
                    ORDER BY i."created_at" DESC
                    """, (target_sold_status,))

                    data = cursor.fetchall()
                    self.display_source_data(data)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def display_source_data(self, data: List[tuple]):
        self.sourceModel.clear()
        source_georgian_headers = [
            'ქვითრის კოდი',
            'პროდუქტის სახელი',
            'რაოდენობა',
            'ერთეულის რაოდენობა',
            'პროდუქტის ფასი',
            'მთლიანი ფასი',
            'ოპერატორი',
            'თარიღი',
            'სტატუსი'  # Added status column
        ]
        self.sourceModel.setHorizontalHeaderLabels(source_georgian_headers)

        if data:
            self.sourceModel.beginInsertRows(QModelIndex(), 0, len(data) - 1)
            for row_data in data:
                # Create items for the row
                row_items = [QStandardItem(str(cell_data)) for cell_data in row_data[:8]]

                # Add Status Text manually based on the boolean
                is_sold = row_data[8]
                status_text = "გაყიდულია" if is_sold else "დაბრუნებულია"
                row_items.append(QStandardItem(status_text))

                # Tooltips
                row_items[0].setToolTip(f"პროდუქტის დასახელება: {row_data[1]}")
                row_items[6].setToolTip(f"ოპერატორი: {row_data[6]}")

                self.sourceModel.appendRow(row_items)
            self.sourceModel.endInsertRows()

        self.checkouts.resizeColumnsToContents()
        self.checkouts.resizeRowsToContents()

    def product_return(self):
        """Returns a selected product to stock and marks it as 'Not Sold'."""
        selected = self.checkouts.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "გაფრთხილება", "გთხოვთ, აირჩიეთ დასაბრუნებელი პროდუქტი.")
            return

        row = selected[0].row()
        invoice_id = self.sourceModel.item(row, 0).text()
        product_name = self.sourceModel.item(row, 1).text()
        quantity_str = self.sourceModel.item(row, 2).text()

        # Check if already returned
        status_item = self.sourceModel.item(row, 8)
        if status_item and status_item.text() == "დაბრუნებულია":
            QMessageBox.warning(self, "შეცდომა", "ეს პროდუქტი უკვე დაბრუნებულია.")
            return

        reply = QMessageBox.question(self, "დაბრუნების დადასტურება",
                                     f"დარწმუნებული ხართ, რომ გსურთ პროდუქტის დაბრუნება: {product_name}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                quantity = float(quantity_str)
                with db.connect() as conn:
                    with conn.cursor() as cursor:
                        # 1. Find the product Code
                        cursor.execute(
                            "SELECT \"COD_MAT\" FROM public.mater1 WHERE \"NAM_MAT\" = %s",
                            (product_name,)
                        )
                        cod_mat = cursor.fetchone()

                        if cod_mat:
                            # 2. Add Quantity back to Stock (Nashti)
                            cursor.execute(
                                """
                                UPDATE public.nashti 
                                SET "NAST" = "NAST" + %s 
                                WHERE "COD_MAT" = %s
                                """,
                                (quantity, cod_mat[0])
                            )

                            # 3. Mark as UNSOLD (False) in Operations
                            # (Instead of Deleting)
                            cursor.execute(
                                """
                                UPDATE public.operations 
                                SET sold = FALSE 
                                WHERE "invoice_id" = %s AND "product_name" = %s
                                """,
                                (invoice_id, product_name)
                            )

                            conn.commit()
                            QMessageBox.information(self, "წარმატება", "პროდუქტი წარმატებით დაბრუნდა.")

                            # Refresh Data
                            self.load_data()

                            # Emit signal to update Merchant Table
                            self.product_returned.emit()

                        else:
                            QMessageBox.warning(self, "შეცდომა",
                                                f"პროდუქტი '{product_name}' მონაცემთა ბაზაში ვერ მოიძებნა.")

            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"პროდუქტის დაბრუნება ვერ მოხერხდა: {e}")

    def invoice_print(self):
        """Generates and prints the invoice for the selected record."""
        selected = self.checkouts.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "გაფრთხილება", "გთხოვთ, აირჩიეთ დასაბეჭდი ქვითარი.")
            return

        row = selected[0].row()
        invoice_id = self.sourceModel.item(row, 0).text()

        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    # Get the main invoice details
                    cursor.execute(
                        "SELECT * FROM public.invoices WHERE invoice_id = %s",
                        (invoice_id,)
                    )
                    invoice_record = cursor.fetchone()

                    if not invoice_record:
                        QMessageBox.warning(self, "შეცდომა", "ქვითარი ვერ მოიძებნა.")
                        return

                    # Get all items for this invoice
                    cursor.execute(
                        "SELECT product_name, quantity, item_quantity, price FROM public.operations WHERE invoice_id = %s",
                        (invoice_id,)
                    )
                    operation_records = cursor.fetchall()

            # Construct context
            invoice_context = {
                'invoice_number': invoice_record[0],
                'created_date': invoice_record[3].strftime('%Y-%m-%d / %H:%M:%S'),
                'total_price': f"{invoice_record[2]:.2f}",
                'items': [
                    {'პროდუქტის სახელი': row[0], 'რაოდენობა': row[1], 'ერთეულის რაოდენობა': row[2], 'ფასი': row[3]}
                    for row in operation_records
                ]
            }

            # Generate PDF
            template_loader = jinja2.FileSystemLoader('./')
            template_env = jinja2.Environment(loader=template_loader)
            template = template_env.get_template('invoice.html')
            output_text = template.render(invoice_context)

            config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
            filename = f'Invoice({invoice_record[3].strftime("%Y-%m-%d")})#{invoice_id}.pdf'
            full_path = os.path.join('invoices', filename)

            if not os.path.exists('invoices'):
                os.makedirs('invoices')

            pdfkit.from_string(output_text, full_path, configuration=config)

            QMessageBox.information(self, 'ინვოისის ამობეჭდვა', 'ინვოისი წარმატებით შეიქმნა! გსურთ ამობეჭდვა?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            os.startfile(full_path)
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"ინვოისის შექმნა ვერ მოხერხდა: {e}")

    def _apply_filter(self, filter_text, column):
        """Helper method to apply filtering to a specific column"""
        for row in range(self.sourceModel.rowCount()):
            item = self.sourceModel.item(row, column)
            match = item is not None and filter_text in item.text().lower()
            self.checkouts.setRowHidden(row, not match)

    def filter_item_with_code(self):
        filter_text = self.code_filter.text().lower()
        self._apply_filter(filter_text, column=0)

    def filter_item_with_date(self):
        filter_text = self.date_filter.text().lower()
        self._apply_filter(filter_text, column=7)