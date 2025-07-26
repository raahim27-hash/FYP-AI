# ocr_processor.py
import cv2
import pytesseract
import os
import json
import re
from collections import defaultdict
from groq import Groq
# import numpy as np # Not used in the provided snippet

# Make sure to set this if tesseract is not in your PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Example for Windows

def preprocess_image_for_ocr(image_path):
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Image not found or could not be read at {image_path}")
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Using GaussianBlur instead of fastNlMeansDenoising for potentially faster processing
    # and often good enough results. fastNlMeansDenoising can be slow.
    blurred = cv2.GaussianBlur(gray, (5, 5), 0) 
    # denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21) # Keep if you prefer
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    contrast_enhanced = clahe.apply(blurred) # or denoised
    thresh = cv2.adaptiveThreshold(
        contrast_enhanced, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, # Inverted threshold can sometimes work better
        11, 
        2
    )
    return thresh

def convert_to_valid_json(json_str):
    try:
        # Remove comments
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL | re.MULTILINE)
        # Replace single quotes with double quotes for keys and string values
        # This regex is a bit simplistic, might need refinement for complex cases
        json_str = re.sub(r"(?<!\\)'([^']*)'", r'"\1"', json_str)
        # Handle specific problematic patterns observed
        json_str = json_str.replace('"price": missing (cannot extract price)', '"price": null')
        json_str = json_str.replace("None", "null") # Python None to JSON null
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        return json_str
    except Exception as e:
        print(f"Error in convert_to_valid_json: {e}")
        return None

def process_receipt(image_path, groq_client):
    """
    Processes a receipt image and returns extracted items.
    Returns: list of dicts [{'item': str, 'price': float, 'category': str}] or None
    """
    print(f"Processing receipt: {image_path}")
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return None

    preprocessed_image = preprocess_image_for_ocr(image_path)
    if preprocessed_image is None:
        print("Preprocessing failed.")
        return None

    # Try different PSM modes if initial extraction is poor
    extracted_text = ""
    psm_modes = [6, 3, 4, 11, 12, 1] # Common PSM modes
    for psm in psm_modes:
        custom_config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist="0123456789$.,€£ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz /-"'
        text = pytesseract.image_to_string(preprocessed_image, config=custom_config).strip()
        if len(text) > len(extracted_text): # Take the one that extracts more text
             extracted_text = text
        if len(extracted_text) > 50 : # Arbitrary threshold for "good enough"
            break 
    
    if not extracted_text:
        print("OCR failed to extract text.")
        return None
    
    print(f"Extracted text (first 200 chars): {extracted_text[:200]}")

    prompt = f"""
    Analyze the following OCR text from a receipt.
    Extract a list of items purchased, their prices, and categorize each item.
    Return the result ONLY as a valid JSON array of objects. Each object must have 'item', 'price' (as a number), and 'category' keys.
    If a price cannot be determined for an item, use null for the price.
    Categories could be like: Groceries, Electronics, Clothing, Restaurant, Pharmacy, Entertainment, Travel, Utilities, Other.

    Receipt Text:
    ---
    {extracted_text}
    ---

    JSON Output:
    """

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192", # or "mixtral-8x7b-32768"
            temperature=0.1 # Lower temperature for more deterministic output
        )
        response_content = chat_completion.choices[0].message.content.strip()
        print(f"LLM Response: {response_content}")

        # Extract JSON part (often LLMs add explanations before/after the JSON block)
        json_match = re.search(r'\[.*\]', response_content, re.DOTALL | re.MULTILINE)
        if not json_match:
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL | re.MULTILINE) # for single object
            if json_match: # if single object, wrap in array
                 response_content = f"[{json_match.group(0)}]"
                 json_match = re.search(r'\[.*\]', response_content, re.DOTALL | re.MULTILINE)


        if not json_match:
            print("No JSON array found in LLM response.")
            # Try to find json objects if not an array
            obj_matches = list(re.finditer(r'\{.*?\}', response_content, re.DOTALL | re.MULTILINE))
            if obj_matches:
                json_str = "[" + ",".join([m.group(0) for m in obj_matches]) + "]"
            else:
                return None
        else:
            json_str = json_match.group(0)

        valid_json_str = convert_to_valid_json(json_str)
        if not valid_json_str:
            print("Failed to convert to valid JSON.")
            return None
        
        categorized_items = json.loads(valid_json_str)

        # Validate structure and convert price
        processed_items = []
        for item_data in categorized_items:
            if isinstance(item_data, dict) and 'item' in item_data and 'price' in item_data and 'category' in item_data:
                try:
                    price = item_data.get('price')
                    if price is not None:
                        # Remove currency symbols and other non-numeric characters before float conversion
                        price_str = str(price).replace('$', '').replace('€', '').replace('£', '').strip()
                        price = float(price_str)
                    else:
                        price = 0.0 # Default if price is null
                except (ValueError, TypeError):
                    price = 0.0 # Default if conversion fails
                
                processed_items.append({
                    'item': str(item_data.get('item', 'Unknown')),
                    'price': price,
                    'category': str(item_data.get('category', 'Uncategorized'))
                })
        
        if not processed_items:
            print("No valid items extracted after processing.")
            return None
            
        return processed_items

    except Exception as e:
        import traceback
        print(f"Error during LLM call or JSON parsing: {e}")
        traceback.print_exc()
        return None

# # Example usage (for testing this file directly)
# if __name__ == "__main__":
#     from dotenv import load_dotenv
#     load_dotenv()
#     api_key = os.environ.get("GROQ_API_KEY")
#     if not api_key:
#         print("GROQ_API_KEY not found in .env file.")
#     else:
#         test_client = Groq(api_key=api_key)
#         # Create a dummy image for testing if you don't have one
#         # For example, a simple text image:
#         # import numpy as np
#         # dummy_image = np.zeros((100, 400, 3), dtype=np.uint8)
#         # cv2.putText(dummy_image, "Item A 10.99 Food", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
#         # cv2.putText(dummy_image, "Item B 5.50 Drinks", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
#         # cv2.imwrite("dummy_receipt.png", dummy_image)
#         # image_file = "dummy_receipt.png"

#         image_file = input("Enter the name of the receipt image file (e.g., 'receipt.jpg'): ").strip()
#         if os.path.exists(image_file):
#             results = process_receipt(image_file, test_client)
#             if results:
#                 print("\nProcessed Items:")
#                 for item in results:
#                     print(f"  Item: {item['item']}, Price: {item['price']:.2f}, Category: {item['category']}")
#             else:
#                 print("No results from receipt processing.")
#         else:
#             print(f"Test image '{image_file}' not found.")