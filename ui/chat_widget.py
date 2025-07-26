# ui/chat_widget.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                               QTextEdit, QLineEdit, QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QColor, QTextCharFormat, QFont,QTextCursor

# Assuming llm_clients.py is in the parent directory or Python path

from llm_clients import query_groq, query_google_cloud_llm, query_local_llm, FINANCIAL_CONTEXT_DATA

class ChatWidget(QWidget):
    # Signal to notify MainWindow about credit changes
    # Args: model_name (str), cost (int)
    message_sent = Signal(str, int) 
    # Signal to update credit display immediately
    credits_updated = Signal(int)

    MODEL_OPTIONS = {
        "Expert (100 credits)": {"api": query_groq, "cost": 100},
        "Advanced (10 credits)": {"api": query_google_cloud_llm, "cost": 10},
        "Basic (Free)": {"api": query_local_llm, "cost": 0}
    }

    def __init__(self, initial_credits=500):
        super().__init__()
        self.current_credits = initial_credits
        self.current_model_name = list(self.MODEL_OPTIONS.keys())[0]
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Model Selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Select your financial advisor:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(self.MODEL_OPTIONS.keys())
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)

        # Chat Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setObjectName("chatDisplay")
        font = QFont()
        font.setPointSize(20)  # Increase font size
        self.chat_display.setFont(font)
        layout.addWidget(self.chat_display, 1)

        # Input Area
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your financial question here...")
        self.message_input.setMinimumHeight(120)  # Increased height
        self.message_input.setFont(QFont("Arial", 20))  # Slightly larger input font
        self.message_input.returnPressed.connect(self._send_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumHeight(40)  # Match height with input
        self.send_button.setFont(QFont("Arial", 16))  # Consistent font size
        self.send_button.clicked.connect(self._send_message)

        input_layout.addWidget(self.message_input, 1)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        self.setLayout(layout)
        self._update_send_button_state()


    def _on_model_changed(self, model_name):
        if self.current_model_name != model_name:
            self.current_model_name = model_name
            self.chat_display.clear() # Clear history on model switch
            self._add_system_message(f"Switched to {model_name}. Chat history cleared.")
            self._update_send_button_state()

    def _add_message_to_display(self, sender, message, color):
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End) # <--- CORRECTED
        cursor = self.chat_display.textCursor()
        
        # Sender format
        sender_format = QTextCharFormat()
        sender_format.setFontWeight(QFont.Bold)
        sender_format.setFontPointSize(20)  # Font size for sender
        sender_format.setForeground(QColor(color))
        cursor.insertText(f"{sender}: ", sender_format)
        
        # Message format
        message_format = QTextCharFormat()
        message_format.setForeground(QColor("#D8DEE9")) # Default text color
        message_format.setFontPointSize(20)  # Font size for sender

        cursor.insertText(message + "\n\n", message_format)
        
        self.chat_display.ensureCursorVisible()

    def _add_system_message(self, message):
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End) # <--- CORRECTED
        cursor = self.chat_display.textCursor()
        msg_format = QTextCharFormat()
        msg_format.setFontItalic(True)
        msg_format.setForeground(QColor("#81A1C1")) # Nord Frost lighter
        msg_format.setFontPointSize(20)  # Slightly smaller if you prefer
        cursor.insertText(f"System: {message}\n\n", msg_format)
        self.chat_display.ensureCursorVisible()


    def _send_message(self):
        user_message = self.message_input.text().strip()
        if not user_message:
            return

        selected_model_key = self.model_combo.currentText()
        model_info = self.MODEL_OPTIONS[selected_model_key]
        cost = model_info["cost"]

        if self.current_credits < cost:
            QMessageBox.warning(self, "Insufficient Credits",
                                f"You need {cost} credits for this model, but you only have {self.current_credits}.")
            return

        self._add_message_to_display("You", user_message, "#A3BE8C") # Nord Aurora Green for user
        self.message_input.clear()
        self.message_input.setEnabled(False) # Disable input while processing
        self.send_button.setEnabled(False)

        # Deduct credits and emit signal (MainWindow will handle actual deduction and update)
        self.message_sent.emit(selected_model_key, cost) 
        # The MainWindow will call update_internal_credits to sync this widget's credit count

        # Call the LLM (this should ideally be in a QThread for non-blocking UI)
        llm_api_func = model_info["api"]
        # For demo, passing the global financial data. In a real app, this might be dynamic.
        response = llm_api_func(user_message, FINANCIAL_CONTEXT_DATA) 
        
        self._add_message_to_display(selected_model_key, response, "#B48EAD") # Nord Aurora Purple for AI

        self.message_input.setEnabled(True)
        self._update_send_button_state()
        self.message_input.setFocus()


    def update_internal_credits(self, new_credits):
        self.current_credits = new_credits
        self._update_send_button_state()

    def _update_send_button_state(self):
        selected_model_key = self.model_combo.currentText()
        cost = self.MODEL_OPTIONS[selected_model_key]["cost"]
        can_afford = self.current_credits >= cost
        self.send_button.setEnabled(can_afford)
        if not can_afford:
            self.send_button.setToolTip(f"Not enough credits ({self.current_credits} available, {cost} needed)")
        else:
            self.send_button.setToolTip("")