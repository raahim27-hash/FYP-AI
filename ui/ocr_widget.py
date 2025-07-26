# ui/ocr_widget.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QProgressDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage

# Assuming ocr_processor.py is in the parent directory or Python path

from ocr_processor import process_receipt
from llm_clients import groq_client_instance # Use the shared Groq client

# Worker thread for OCR processing to avoid freezing UI
class OCRWorker(QThread):
    finished = Signal(object)  # object will be the list of items or None
    error = Signal(str)

    def __init__(self, image_path, client):
        super().__init__()
        self.image_path = image_path
        self.client = client

    def run(self):
        try:
            if not self.client:
                self.error.emit("Groq client not initialized. Check API key.")
                return
            # This is a blocking call, so it runs in this thread
            results = process_receipt(self.image_path, self.client)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(f"OCR processing error: {str(e)}")


class OCRWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._selected_image_path = None
        self.ocr_thread = None # To hold the worker thread
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Image Selection and Preview
        select_layout = QHBoxLayout()
        self.select_image_button = QPushButton("Select Receipt Image")
        self.select_image_button.clicked.connect(self._select_image)
        select_layout.addWidget(self.select_image_button)
        
        self.image_preview_label = QLabel("No image selected.")
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setMinimumHeight(150) # Min height for preview
        self.image_preview_label.setStyleSheet("border: 1px dashed #4C566A; background-color: #353C4A;")
        
        select_layout.addWidget(self.image_preview_label, 1) # Takes remaining space
        layout.addLayout(select_layout)

        # Process Button
        self.process_button = QPushButton("Extract Items from Receipt")
        self.process_button.clicked.connect(self._start_ocr_processing)
        self.process_button.setEnabled(False) # Enabled when image is selected
        layout.addWidget(self.process_button)

        # Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Item", "Price", "Category"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers) # Read-only
        self.results_table.setAlternatingRowColors(True) # Nice for readability
        layout.addWidget(self.results_table, 1) # Takes most space

        self.setLayout(layout)

    def _select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Receipt Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            self._selected_image_path = file_path
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                self.image_preview_label.setText("Cannot display image.")
                self.process_button.setEnabled(False)
            else:
                # Scale pixmap to fit label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(self.image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview_label.setPixmap(scaled_pixmap)
                self.process_button.setEnabled(True)
            self.results_table.setRowCount(0) # Clear previous results

    def _start_ocr_processing(self):
        if not self._selected_image_path:
            QMessageBox.warning(self, "No Image", "Please select an image first.")
            return
        if not groq_client_instance:
            QMessageBox.critical(self, "API Error", "Groq client not available. Please check your GROQ_API_KEY in the .env file.")
            return

        self.process_button.setEnabled(False)
        self.select_image_button.setEnabled(False)
        self.results_table.setRowCount(0)

        # Setup progress dialog
        self.progress_dialog = QProgressDialog("Processing receipt...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(True) # Automatically close when thread finishes
        self.progress_dialog.canceled.connect(self._cancel_ocr)
        
        # Start worker thread
        self.ocr_thread = OCRWorker(self._selected_image_path, groq_client_instance)
        self.ocr_thread.finished.connect(self._on_ocr_finished)
        self.ocr_thread.error.connect(self._on_ocr_error)
        self.ocr_thread.start()
        self.progress_dialog.show()


    def _on_ocr_finished(self, results):
        self.progress_dialog.close()
        self.process_button.setEnabled(True)
        self.select_image_button.setEnabled(True)

        if results:
            self.results_table.setRowCount(len(results))
            for row_idx, item_data in enumerate(results):
                self.results_table.setItem(row_idx, 0, QTableWidgetItem(item_data.get('item', 'N/A')))
                self.results_table.setItem(row_idx, 1, QTableWidgetItem(f"{item_data.get('price', 0.0):.2f}"))
                self.results_table.setItem(row_idx, 2, QTableWidgetItem(item_data.get('category', 'N/A')))
            QMessageBox.information(self, "Success", f"Successfully extracted {len(results)} items.")
        else:
            self.results_table.setRowCount(0)
            QMessageBox.warning(self, "OCR Failed", "Could not extract items from the receipt. The image might be unclear, or the format not recognized.")
        
        self.ocr_thread = None # Clear thread reference


    def _on_ocr_error(self, error_message):
        self.progress_dialog.close()
        self.process_button.setEnabled(True)
        self.select_image_button.setEnabled(True)
        QMessageBox.critical(self, "OCR Error", error_message)
        self.ocr_thread = None

    def _cancel_ocr(self):
        if self.ocr_thread and self.ocr_thread.isRunning():
            self.ocr_thread.terminate() # Force terminate
            self.ocr_thread.wait()      # Wait for it to finish
            QMessageBox.information(self, "Cancelled", "OCR processing was cancelled.")
        self.progress_dialog.close()
        self.process_button.setEnabled(True)
        self.select_image_button.setEnabled(True)
        self.ocr_thread = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._selected_image_path: # Rescale preview on window resize
            pixmap = QPixmap(self._selected_image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview_label.setPixmap(scaled_pixmap)