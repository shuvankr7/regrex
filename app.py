import re
import json
from urllib.parse import urlparse
from fuzzywuzzy import process
import warnings
import time
import nltk
from nltk.corpus import stopwords



# Download NLTK stopwords if not already downloaded
nltk.download('stopwords')

# Load NLTK stopwords
nltk_stopwords = set(stopwords.words('english'))

# Load merchant dataset
with open('small marchent.json', 'r') as file:
    merchant_dataset = json.load(file)

def extract_transaction_info(message):
    """
    Extracts transaction details from an SMS message, including amount, transaction type, merchant, and payment method.
    """
    # Replace URLs with domain names
    message = re.sub(r'https?://[^\s]+', lambda match: urlparse(match.group(0)).netloc, message)
    message_lower = message.lower()
    
    # Define keywords
    debit_keywords = ['debited', 'withdrawn', 'spent', 'paid', 'deducted', 'charged', 'purchase', 'payment', 'transfer', 'debit', 'sent']
    credit_keywords = ['credited', 'deposited', 'received', 'added', 'refund', 'reversed', 'refunded']
    transaction_keywords = debit_keywords + credit_keywords
    non_transactional_keywords = ['will', 'otp', 'password', 'login', 'verification', 'code', 'alert', 'update']

    # Define regex patterns
    amount_pattern = re.compile(r'(?i)(?:RS|INR|MRP)?\.?\s?(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?)')
    entity_pattern = re.compile(r'\b(at|from|to|via|through|with)\s+(.+?)(?=\s+\b(?:at|from|to|via|through|with)|\s*$)', re.IGNORECASE)
    merchant_pattern = re.compile(r'(?i)(?:\sat\s|in\*)([A-Za-z0-9]*\s?-?\s?[A-Za-z0-9]*\s?-?\s?)')
    card_bank_upi_pattern = re.compile(r'(?i)(?:\smade on|ur|made a\s|in\*)([A-Za-z]+(?:\s?-?\s[A-Za-z]+)*)')
    
    # Check if non-transactional
    if any(keyword in message_lower for keyword in non_transactional_keywords):
        return {"status": "Non-transactional message."}
    
    # Check for transaction keywords and amount
    has_keyword = any(keyword in message_lower for keyword in transaction_keywords)
    amount_match = amount_pattern.search(message)
    
    if not (has_keyword and amount_match):
        return {"status": "Non-transactional message."}
    
    # Extract transaction amount
    amount = amount_match.group(1).replace(',', '')
    transaction_type = 'debit' if any(keyword in message_lower for keyword in debit_keywords) else 'credit'
    
    # Extract entities (merchant, bank/UPI)
    entities = entity_pattern.findall(message)
    merchants, bank_upi_card = [], None
    
    for preposition, entity in entities:
        if preposition.lower() in ['at', 'to']:
            merchants.append(entity)
        elif preposition.lower() in ['via', 'through', 'with', 'your', 'from'] and not bank_upi_card:
            bank_upi_card = entity
    
    # Extract merchant via regex
    merchant_match = merchant_pattern.search(message)
    merchant = merchant_match.group(1).strip() if merchant_match else (merchants[0].strip() if merchants else None)
    
    # Filter out merchants that are purely numeric
    if merchant and merchant.isdigit():
        merchant = None
    
    # Keep the original merchant name intact
    original_merchant = merchant
    
    # Truncate merchant name at the first stopword or invalid character for tag searching
    truncated_merchant = None
    if merchant:
        merchant_parts = merchant.split()
        truncated_parts = []
        for part in merchant_parts:
            if part.lower() in nltk_stopwords:  # Use globally defined nltk_stopwords
                break
            truncated_parts.append(part)
        truncated_merchant = ' '.join(truncated_parts).strip()
    
    # Extract card/bank/UPI via regex
    card_bank_upi_match = card_bank_upi_pattern.search(message)
    bank_upi_card = card_bank_upi_match.group(1).strip() if card_bank_upi_match else bank_upi_card
    
    # Match merchant with dataset using fuzzy matching
    tag = None
    if truncated_merchant:  # Use truncated merchant for tag searching
        for category, merchant_list in merchant_dataset.items():
            best_match, score = process.extractOne(truncated_merchant.lower(), [m.lower() for m in merchant_list])
            if score > 80:  # Use a threshold for fuzzy matching
                tag = category
                break
    
    # Return extracted details
    return {
        "status": "Success",
        "amount": amount,
        "transaction_type": transaction_type,
        "merchant": original_merchant if original_merchant else "N/A",  # Use original merchant name
        "bank_upi_card": bank_upi_card if bank_upi_card else "N/A",
        "tag": tag if tag else "Uncategorized"
    }

if __name__ == "__main__":
    print("Transaction Info Extractor")
    msg = input("Enter the SMS message: ")
    result = extract_transaction_info(msg)
    if result["status"] == "Success":
        # Preprocess the merchant name to truncate at the first stopword
        merchant = result['merchant']
        if merchant != "N/A":
            merchant_parts = merchant.split()
            truncated_parts = []
            for part in merchant_parts:
                if part.lower() in nltk_stopwords:  # Use globally defined nltk_stopwords
                    break
                truncated_parts.append(part)
            merchant = ' '.join(truncated_parts).strip()
        
        # Print the results
        print(f"Amount: {result['amount']}")
        print(f"Transaction Type: {result['transaction_type']}")
        print(f"Merchant: {merchant}")
        print(f"Bank/UPI/Card: {result['bank_upi_card']}")
        print(f"Tag: {result['tag']}")
    else:
        print(result["status"])
