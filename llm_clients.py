# llm_clients.py
import os
import time
import json
import requests # For making HTTP requests
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

# Attempt to import Google Auth libraries for Cloud Run authentication
try:
    import google.auth
    import google.auth.transport.requests
    from google.oauth2 import id_token
    from google.auth import jwt
    # from google.oauth2 import id_token # This is already imported in the function, which is fine.
    google_auth_available = True
except ImportError:
    google_auth_available = False
    print("Warning: google-auth library not installed. Authentication for Google Cloud Run may fail if required.")
    # For the function to not break if google.auth is not available,
    # we might need to ensure id_token is also conditionally accessed or
    # ensure the function query_google_cloud_llm itself checks google_auth_available.
    # However, for this specific use case, we assume it will be available if GCP is used.

# --- System Prompt Definition ---
FINANCIAL_ASSISTANT_SYSTEM_PROMPT = """
You are an AI Financial Assistant, designed to provide helpful, clear, and comprehensive information and educational guidance on a wide range of personal finance topics. Your goal is to empower users to better understand their finances and make informed decisions.

Your Capabilities Include (but are not limited to):

General Financial Literacy: Explaining core financial concepts (e.g., inflation, interest rates, compound interest, assets, liabilities, net worth).
Budgeting and Saving: Offering strategies for creating budgets, tracking expenses, developing savings plans, and setting financial goals.
Debt Management: Providing information on different types of debt (credit cards, loans, mortgages), strategies for debt reduction, and understanding credit scores.
Investment Education:
Explaining different investment types (stocks, bonds, mutual funds, ETFs, real estate, cryptocurrencies – explaining what they are, not recommending specific ones).
Discussing basic investment principles (diversification, risk tolerance, long-term vs. short-term investing, asset allocation).
Explaining how financial markets work at a high level.
Defining common investment jargon.
Financial Planning Basics: Information on retirement planning concepts (e.g., types of retirement accounts available in general or specific to a region if you have that knowledge), saving for major purchases (e.g., a house, education), and emergency funds.
Understanding Financial Products: Explaining how products like insurance (health, life, auto), bank accounts, and credit cards work.
Economic Awareness: Discussing general economic indicators and trends and how they might impact personal finances (use your knowledge up to your last update, and mention if information might be outdated for very current events).
Financial Goal Setting: Helping users think through and articulate their financial goals.
Your Interaction Style:

Be patient, empathetic, and encouraging.
Break down complex topics into smaller, digestible pieces.
Use examples or analogies to clarify concepts.
If you don't know something or if a question goes beyond your scope as an educational tool, say so.
Now, please begin. I am here to ask for your financial guidance and information.
"""

# --- Groq Client ---
groq_api_key = os.environ.get("GROQ_API_KEY")
groq_client_instance = None
if groq_api_key:
    groq_client_instance = Groq(api_key=groq_api_key)
else:
    print("Warning: GROQ_API_KEY not found. Groq functionality will be disabled.")

def query_groq(prompt_text, financial_data_context=""):
    if not groq_client_instance:
        return "Error: Groq API key not configured."

    user_content = ""
    if financial_data_context and financial_data_context.strip(): # Add context only if it's non-empty
        user_content += f"Financial Context:\n{financial_data_context}\n\n"
    user_content += f"User Question: {prompt_text}"

    try:
        chat_completion = groq_client_instance.chat.completions.create(
            messages=[
                {"role": "system", "content": FINANCIAL_ASSISTANT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            model="llama-3.1-8b-instant", # Or "mixtral-8x7b-32768"
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error querying Groq: {e}"

# --- Google Cloud LLM Client (Ollama on Cloud Run) ---
GCP_OLLAMA_RUN_URL = os.environ.get("GCP_OLLAMA_RUN_URL")
# GCP_OLLAMA_MODEL_NAME = os.environ.get("GCP_OLLAMA_MODEL_NAME") # Commented out to use hardcoded value
# The GOOGLE_APPLICATION_CREDENTIALS environment variable is used by google-auth
# to load credentials when it's set.
GCP_OLLAMA_MODEL_NAME = "gemma3:27b" # Hardcoded model name for testing

def query_google_cloud_llm(prompt_text, financial_data_context=""):
    if not google_auth_available:
        return "Error: Google Auth libraries not available. Cannot call GCP LLM."
    if not GCP_OLLAMA_RUN_URL:
        print("Error: GCP_OLLAMA_RUN_URL not configured. Please set it in your environment.")
        return "Error: GCP_OLLAMA_RUN_URL not configured."
    if not GCP_OLLAMA_MODEL_NAME: # Should not happen with hardcoding but good practice
        print(f"!!! CRITICAL ERROR: GCP_OLLAMA_MODEL_NAME is not set or empty. Value: '{GCP_OLLAMA_MODEL_NAME}'")
        return "Error: GCP_OLLAMA_MODEL_NAME not configured or empty."

    audience = GCP_OLLAMA_RUN_URL.rstrip('/')
    api_url = f"{audience}/api/chat"

    headers = {"Content-Type": "application/json"}

    user_content = ""
    if financial_data_context and financial_data_context.strip():
        user_content += f"Financial Context:\n{financial_data_context}\n\n"
    user_content += f"User Question: {prompt_text}"

    messages = [
        {"role": "system", "content": FINANCIAL_ASSISTANT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    payload = {
        "model": GCP_OLLAMA_MODEL_NAME,
        "messages": messages,
        "stream": False, # Set to True for streaming if you want to handle it
        "options": {
            "temperature": 0.7
        }
    }

    try:
        print("DEBUG: Attempting to fetch ID token for Cloud Run...")
        auth_req = google.auth.transport.requests.Request()
        # Ensure google.oauth2.id_token is accessible
        id_token_val = google.oauth2.id_token.fetch_id_token(auth_req, audience)

        if not id_token_val:
            print("Error: Could not fetch ID token using service account. "
                  "Check GOOGLE_APPLICATION_CREDENTIALS path and key validity.")
            return "Error: Could not fetch ID token."

        headers["Authorization"] = f"Bearer {id_token_val}"
        print(f"DEBUG: Successfully fetched ID token. Authorization header set.")

        print("-" * 50)
        print(f"DEBUG: Authenticating as Service Account (via GOOGLE_APPLICATION_CREDENTIALS).")
        print(f"DEBUG: GCP_OLLAMA_RUN_URL='{GCP_OLLAMA_RUN_URL}' (Audience: '{audience}')")
        print(f"DEBUG: GCP_OLLAMA_MODEL_NAME='{GCP_OLLAMA_MODEL_NAME}'")
        print(f"DEBUG: Target API URL='{api_url}'")
        print(f"DEBUG: Payload being sent to Ollama:\n{json.dumps(payload, indent=2)}")
        print("-" * 50)

        print(f"Attempting to call: {api_url} with model: {GCP_OLLAMA_MODEL_NAME}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=600) # Increased timeout further

        print(f"Cloud Run Response Status: {response.status_code}")
        response.raise_for_status()

        response_json = response.json()

        if "message" in response_json and "content" in response_json["message"]:
            return response_json["message"]["content"].strip()
        elif "error" in response_json:
            return f"Ollama API Error on Cloud Run: {response_json['error']}"
        else:
            print(f"Unexpected Ollama response structure: {response_json}")
            return "Error: Received unexpected response format from Ollama on Cloud Run."

    except google.auth.exceptions.DefaultCredentialsError as e:
        print(f"Google Auth DefaultCredentialsError: {e}")
        print("Ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly to your service account key file path. "
              "The service account also needs 'roles/run.invoker' on the Cloud Run service.")
        return "Error: Google authentication failed (service account credentials error)."
    except google.auth.exceptions.RefreshError as e:
        print(f"Google Auth RefreshError: {e}")
        print("Issue refreshing credentials for service account. Check key validity or network access to auth servers.")
        return "Error: Could not refresh Google authentication token (service account)."
    except requests.exceptions.HTTPError as http_err:
        error_content = "No additional error content from server."
        if http_err.response is not None:
            try:
                error_content_json = http_err.response.json()
                error_content = f"Server Response (JSON): {error_content_json}"
            except json.JSONDecodeError:
                error_content = f"Server Response (Text): {http_err.response.text}"
        print(f"HTTP error occurred calling Ollama on Cloud Run: {http_err} - {error_content}")
        return f"HTTP error occurred: {http_err.response.status_code if http_err.response else 'Unknown'}. Check logs for details."
    except requests.exceptions.Timeout:
        print("Error: Request to Ollama on Cloud Run timed out after 600 seconds.")
        return "Error: Request to Ollama on Cloud Run timed out."
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred calling Ollama on Cloud Run: {req_err}")
        return f"Request error occurred: {req_err}"
    except Exception as e:
        import traceback
        print("An unexpected error occurred:")
        traceback.print_exc()
        return f"An unexpected error occurred while contacting Ollama on Cloud Run: {type(e).__name__}"

# --- Local LLM Client (as before) ---
def query_local_llm(prompt_text, financial_data_context=""):
    print(f"Simulating Local LLM call for: {prompt_text}")
    time.sleep(0.5) # Simulate processing
    return f"Local LLM response to: '{prompt_text}' (with context: {financial_data_context[:30]}...)"

# --- Financial Data (as before, for testing if needed directly in this file) ---
FINANCIAL_CONTEXT_DATA = """
Transaction History:
- 2023-10-01: Salary Deposit, +$5000
- 2023-10-02: Groceries (SuperMart), -$75.50

Current Balances:
- Checking Account: $4924.50
"""

# Example usage (you would call these from main.py or elsewhere)
if __name__ == "__main__":
    print("--- Testing Groq LLM ---")
    if groq_api_key:
        groq_response = query_groq("What is compound interest?", financial_data_context=FINANCIAL_CONTEXT_DATA)
        print(f"Groq Response:\n{groq_response}\n")
    else:
        print("Groq test skipped (no API key).\n")

    print("--- Testing Google Cloud LLM ---")
    if GCP_OLLAMA_RUN_URL and google_auth_available:
        # Ensure GOOGLE_APPLICATION_CREDENTIALS is set in your environment for this to work
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            print("Attempting GCP LLM call (ensure GOOGLE_APPLICATION_CREDENTIALS is valid)...")
            start_time = time.time()
            gcp_response = query_google_cloud_llm("Explain ETFs.", financial_data_context=FINANCIAL_CONTEXT_DATA)
            end_time = time.time()
            print(f"GCP LLM Response (took {end_time - start_time:.2f} seconds):\n{gcp_response}\n")
        else:
            print("GCP LLM test skipped: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
    else:
        if not GCP_OLLAMA_RUN_URL:
            print("GCP LLM test skipped (GCP_OLLAMA_RUN_URL not set).\n")
        if not google_auth_available:
            print("GCP LLM test skipped (google-auth libraries not available).\n")

    print("--- Testing Local LLM ---")
    local_response = query_local_llm("How to save money?", financial_data_context=FINANCIAL_CONTEXT_DATA)
    print(f"Local LLM Response:\n{local_response}\n")