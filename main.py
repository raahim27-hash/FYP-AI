# main.py
import sys
import os
from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

# Add ui directory to sys.path to allow direct import of MainWindow
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
from ui.main_window import MainWindow # Changed

# For Tesseract OCR, if not in PATH
# import pytesseract
# If you're on Windows and Tesseract is not in PATH:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Or on Linux/macOS, if needed:
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract' # Example path

if __name__ == "__main__":
    load_dotenv() # Load environment variables from .env file (e.g., GROQ_API_KEY)

    # Check if GROQ_API_KEY is loaded (optional, but good for early warning)
    if not os.environ.get("GROQ_API_KEY"):
        print("WARNING: GROQ_API_KEY not found in .env file. Some features might not work.")
        # You could show a QMessageBox here or disable certain UI elements later

    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())