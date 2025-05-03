import json
import os
from PyPDF2 import PdfReader

def extract_text_from_json(json_filepath):
    with open(json_filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Extract relevant fields
    text_data = []
    text_data.append(f"Bank Name: {data['bank_name']}")
    text_data.append(f"Account Holder: {data['account_holder']}")
    text_data.append(f"IBAN: {data['iban']}")
    text_data.append(f"Balance: {data['balance']} {data['currency']}")
    
    # Loans
    for loan in data.get('loans', []):
        text_data.append(f"Loan Type: {loan['type']}, Amount: {loan['amount']}")
    
    # Transactions
    for transaction in data.get('transactions', []):
        text_data.append(f"Transaction on {transaction['date']}: {transaction['description']} "
                         f"({transaction['amount']} {data['currency']})")
    
    return "\n".join(text_data)

def extract_text_from_pdfs(pdf_folder):
    text_data = []
    for filename in os.listdir(pdf_folder):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_folder, filename)
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                text_data.append(page.extract_text())
    return "\n".join(text_data)

def process_files(json_filepath, pdf_folder):
    json_text = extract_text_from_json(json_filepath)
    pdf_text = extract_text_from_pdfs(pdf_folder)
    
    # Combine all extracted text
    combined_text = f"{json_text}\n\n{pdf_text}"
    return combined_text

# Example usage
if __name__ == "__main__":
    json_path = "c:\\Users\\User\\Desktop\\smart-bank-chatbot\\mockdata.json"
    pdf_dir = "c:\\Users\\User\\Desktop\\smart-bank-chatbot"
    context_text = process_files(json_path, pdf_dir)
    print(context_text)  # Replace with appending to conversation history
