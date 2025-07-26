# ui/main_window.py
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QStackedWidget, QLabel, QSpacerItem, QSizePolicy,QMessageBox)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon # If you want to add an icon

from .chat_widget import ChatWidget
from .ocr_widget import OCRWidget

class MainWindow(QMainWindow):
    INITIAL_CREDITS = 500

    def __init__(self):
        super().__init__()
        self.current_credits = self.INITIAL_CREDITS
        self._init_ui()
        self._load_stylesheet() # Load QSS

    def _init_ui(self):
        self.setWindowTitle("AI Finance Demo")
        self.setGeometry(100, 100, 1000, 700) # x, y, width, height
        # self.setWindowIcon(QIcon("path/to/your/icon.png")) # Optional

        # Main container widget
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0) # Full bleed for main layout
        main_layout.setSpacing(0)

        # Header: Navigation and Credits
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10,5,10,5)
        
        self.chat_nav_button = QPushButton("Chat Assistant")
        self.chat_nav_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        self.ocr_nav_button = QPushButton("Receipt OCR")
        self.ocr_nav_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        header_layout.addWidget(self.chat_nav_button)
        header_layout.addWidget(self.ocr_nav_button)
        header_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)) # Spacer
        
        self.credits_label = QLabel(f"Credits: {self.current_credits}")
        self.credits_label.setObjectName("creditsLabel") # For QSS
        header_layout.addWidget(self.credits_label)
        
        main_layout.addWidget(header_widget)

        # Page Titles (optional, but nice)
        self.page_title_label = QLabel("Chat Assistant") # Default title
        self.page_title_label.setObjectName("headerLabel")
        self.page_title_label.setAlignment(Qt.AlignCenter)
        # main_layout.addWidget(self.page_title_label) # Add if you want a prominent title

        # Stacked Widget for Pages
        self.stacked_widget = QStackedWidget()
        
        self.chat_page = ChatWidget(initial_credits=self.INITIAL_CREDITS)
        self.chat_page.message_sent.connect(self._handle_message_sent)
        
        self.ocr_page = OCRWidget()
        
        self.stacked_widget.addWidget(self.chat_page) # Index 0
        self.stacked_widget.addWidget(self.ocr_page)  # Index 1
        self.stacked_widget.currentChanged.connect(self._update_page_title)


        main_layout.addWidget(self.stacked_widget, 1) # Page content takes most space

        self.setCentralWidget(main_widget)
        self._update_page_title(0) # Set initial title

    def _update_page_title(self, index):
        if index == 0:
            self.page_title_label.setText("Chat Assistant")
        elif index == 1:
            self.page_title_label.setText("Receipt OCR Processor")

    @Slot(str, int)
    def _handle_message_sent(self, model_name, cost):
        if self.current_credits >= cost:
            self.current_credits -= cost
            self.credits_label.setText(f"Credits: {self.current_credits}")
            # Notify ChatWidget about its new credit balance (after deduction)
            self.chat_page.update_internal_credits(self.current_credits) 
        else:
            # This case should ideally be caught in ChatWidget, but as a fallback:
            QMessageBox.critical(self, "Credit Error", "Transaction attempted with insufficient credits.")


    def _load_stylesheet(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            style_file_path = os.path.join(current_dir, "assets", "style.qss")
            with open(style_file_path, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("Warning: Stylesheet 'ui/assets/style.qss' not found. Using default styles.")
        except Exception as e:
            print(f"Error loading stylesheet: {e}")
