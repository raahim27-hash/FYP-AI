## 💰 LLM-AI: AI-Powered Financial Assistant with OCR

LLM AI is a desktop application that combines the power of Large Language Models (LLMs) and Optical Character Recognition (OCR) to help users better understand and manage their personal finances. The app features a financial chatbot and a receipt scanner—all integrated into a clean, responsive UI.

---

## 🚀 Features

- 🤖 **AI Financial Assistant**  
  Chat with three LLM tiers (Groq, Google Cloud Ollama, Local) to get insights on budgeting, debt, savings, investments, and more.

- 📷 **Receipt OCR & Analysis**  
  Upload receipt images to automatically extract item names, prices, and categories using OCR + LLM post-processing.

- 💬 **Interactive Chat UI**  
  Real-time messaging interface with message formatting, model selection, and usage-based credit system.

- 🧾 **Structured Results Table**  
  Display of extracted items from receipts in a searchable, categorized table.

- 🌐 **Multimodal Integration**  
  Combines text (chat) and image (OCR) inputs into one intelligent assistant.

---

## 🛠️ Tech Stack

- **Python** (PySide6, OpenCV, Tesseract OCR, requests)
- **LLM APIs**: [Groq](https://groq.com/), Gemini, Google Cloud Run (Ollama), local mock model
- **Threading**: QThread for non-blocking OCR operations
- **Environment Config**: `.env` + `dotenv` for secure API key management

---

## 📂 Project Structure
```bash
📦 LLM-AI
┣ 📜 main.py → App entry point
┣ 📜 llm_clients.py → Handles LLM model queries (Groq, GCP, local)
┣ 📜 ocr_processor.py → Handles image preprocessing + OCR text extraction
┣ 📂 ui/
┃ ┣ 📜 main_window.py → Loads chat + OCR widgets into the main app
┃ ┣ 📜 chat_widget.py → Chat interface for talking to financial LLMs
┃ ┣ 📜 ocr_widget.py → GUI for uploading receipts and viewing extracted data
┣ 📜 .env → API keys & configs (not included)
┣ 📜 README.md → Project documentation
```

---

## 🔑 Getting Started

1. **Install requirements**:
   ```bash
   pip install -r requirements.txt

2. **Set up .env**:
 
GROQ_API_KEY=your_groq_api_key
GCP_OLLAMA_RUN_URL=https://your-cloudrun-url
GOOGLE_APPLICATION_CREDENTIALS=path_to_your_service_account.json

3. **Install Tesseract (if not in PATH)**:
Windows: https://github.com/tesseract-ocr/tesseract/wiki
Linux/macOS: sudo apt install tesseract-ocr

4. **Run the app**:
 python main.py

## 🧠 Example Use Cases
"How can I start saving for retirement?"

Upload a grocery receipt to automatically analyze and categorize expenses.

"What are ETFs and how do they work?"

## 🛡️ License
MIT License. Built for educational, personal finance, and AI exploration purposes.

## 🙌 Credits
Developed by Mohammed Bin Arif(21K-3851) & Raahim Muzaffar Ishtiaq(21K-4617)
Final Year Project – Financial LLMs

##
Let me know if you want help generating a `requirements.txt`, `.gitignore`, or `.env.template` file next! ​​
