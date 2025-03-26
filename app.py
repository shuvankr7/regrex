import re
import json
import streamlit as st
from urllib.parse import urlparse

# Load merchant dataset
with open('final_merchant_dataset.json', 'r') as file:
    merchant_dataset = json.load(file)

def extract_transaction_info(message):
    """
    Process an SMS message to extract transaction details or classify it as non-transactional.
    
    Args:
        message (str): The SMS message to analyze.
    """
    # Replace URLs with their domain names
    url_pattern = re.compile(r'https?://[^\s]+')
    message = url_pattern.sub(lambda match: urlparse(match.group(0)).netloc, message)
    
    # Define transaction keywords
    debit_keywords = ['debited', 'withdrawn', 'spent', 'paid', 'deducted', 'charged', 'purchase', 'payment', 'transfer','debit','purchase']
    credit_keywords = ['credited', 'deposited', 'received', 'added', 'refund','reversed','refunded']
    transaction_keywords = debit_keywords + credit_keywords

    # Define non-transactional keywords
    non_transactional_keywords = ['will', 'otp', 'password', 'login', 'verification', 'code', 'alert', 'update']
    
    # Define regex patterns
    # Amount pattern: matches optional currency symbols (Rs., $, INR) and numbers (with commas or decimals)
    amount_pattern = re.compile(
        r'(?i)(?:(?:RS|INR|MRP)\.?\s?)(\d+(:?\,\d+)?(\,\d+)?(\.\d{1,2})?)'
    )
    # Entity pattern: captures prepositions (at, from, to, via, through, with) followed by entity names
    # Modified to use non-capturing groups in the lookahead
    entity_pattern = re.compile(
        r'\b(at|from|to|via|through|with)\s+(.+?)(?=\s+\b(?:at|from|to|via|through|with)|\s*$)', 
        re.IGNORECASE
    )
    # Corrected merchant pattern: captures merchant names after 'at' or 'in*'
    merchant_pattern = re.compile(
        r'(?i)(?:\sat\s|in\*)([A-Za-z0-9]*\s?-?\s?[A-Za-z0-9]*\s?-?\.?)'
    )
    # Corrected card/bank/UPI pattern: captures card, bank, or UPI names after specific keywords
    card_bank_upi_pattern = re.compile(
        r'(?i)(?:\smade on|ur|made a\s|in\*)([A-Za-z]*\s?-?\s[A-Za-z]*\s?-?\s[A-Za-z]*\s?-?)'
    )
    
    # Convert message to lowercase for case-insensitive keyword checking
    message_lower = message.lower()

    # Check if the message contains any non-transactional keyword
    if any(keyword in message_lower for keyword in non_transactional_keywords):
        st.write("Non-transactional message.")
        return
    
    # Check if any transaction keyword is present
    has_keyword = any(keyword in message_lower for keyword in transaction_keywords)
    
    # Try to extract amount
    amount_match = amount_pattern.search(message)
    has_amount = amount_match is not None
    
    # Classify as transactional if both a keyword and an amount are present
    if has_keyword and has_amount:
        # Extract and clean the amount (remove commas)
        amount = amount_match.group(1).replace(',', '')
        
        # Determine transaction type
        if any(keyword in message_lower for keyword in debit_keywords):
            transaction_type = 'debit'
        elif any(keyword in message_lower for keyword in credit_keywords):
            transaction_type = 'credit'
        else:
            transaction_type = 'unknown'  # Fallback, though unlikely
        
        # Extract entities (merchants and payment methods)
        entities = entity_pattern.findall(message)
        potential_merchants = []
        bank_upi_card = None
        
        for preposition, entity in entities:
            prep = preposition.lower()
            # Merchant typically follows 'at', 'from', 'to'
            if prep in ['at', 'from', 'to']:
                potential_merchants.append(entity)
            # Bank/UPI/Card typically follows 'via', 'through', 'with'
            elif prep in ['via', 'through', 'with','Your'] and bank_upi_card is None:
                bank_upi_card = entity
        
        # Use the provided regex pattern to find the merchant name
        merchant_match = merchant_pattern.search(message)
        if merchant_match:
            merchant = merchant_match.group(1).lower().strip()
        else:
            # Take the last potential merchant as the merchant name
            merchant = potential_merchants[0].split()[:3].lower().casefold().strip() if potential_merchants else None

        # Use the provided regex pattern to find the card, bank, or UPI
        card_bank_upi_match = card_bank_upi_pattern.search(message)
        if card_bank_upi_match:
            bank_upi_card = card_bank_upi_match.group(1).lower().strip()

        # Check if the merchant is in the dataset
        tag = None
        # merchant=merchant.split()[0]
        if merchant:
            for key, merchants in merchant_dataset.items():
                if merchant in merchants:
                    tag = key
                    break
        
        # Output the extracted details
        st.write(f"Amount: {amount}")
        st.write(f"Transaction Type: {transaction_type}")
        st.write(f"Merchant: {merchant if merchant else 'N/A'}")
        st.write(f"Bank/UPI/Card: {bank_upi_card if bank_upi_card else 'N/A'}")
        st.write(f"Tag: {tag}")
    else:
        # If no keyword or no amount, classify as non-transactional
        st.write("Non-transactional message.")

# Streamlit interface
st.title("Transaction Info Extractor")
msg = st.text_area("Enter the SMS message:")
if st.button("Process"):
    st.write("\nProcessing:")
    extract_transaction_info(msg)
