import os
import json

from PyPDF2 import PdfReader

from typing import Dict, List, Optional, TypedDict, Annotated
from typing_extensions import TypedDict

import google.generativeai as genai

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# from .index import process_pdf
# Function to process PDF files and extract text
def process_pdf(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error processing PDF file: {e}")
        return ""


# Read the environment variables
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


# Define our schema for invoice data
class InvoiceData(TypedDict):
    invoice_number: Optional[str]
    date: Optional[str]
    due_date: Optional[str]
    total_amount: Optional[str]
    tax_amount: Optional[str]
    vendor_name: Optional[str]
    vendor_address: Optional[str]
    bank_account: Optional[str]
    bic: Optional[str]
    iban: Optional[str]
    payment_terms: Optional[str]
    currency: Optional[str]
    line_items: Optional[List[Dict]]


# Define the state schema
class State(TypedDict):
    # Messages will be appended to this list using the add_messages function
    messages: Annotated[List, add_messages]
    # The invoice text to analyze
    invoice_text: str
    # The extracted invoice data
    invoice_data: Optional[InvoiceData]
    # Any errors encountered
    error: Optional[str]


# Initialize Google Generative AI with your API key
def setup_gemini_client():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError('Missing GEMINI_API_KEY in environment variables.')
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name="gemini-2.0-flash")


# Extract invoice data from text using Gemini
def extract_invoice_data(state: State):

    model = setup_gemini_client()
    
    # Prepare the prompt
    prompt = f"""
    You are an expert in invoice analysis. 
    Extract the following information from this invoice text:
    - Invoice Number
    - Date
    - Due Date
    - Total Amount
    - Tax Amount
    - Vendor Name
    - Vendor Address
    - Bank Account
    - BIC
    - IBAN
    - Payment Terms
    - Currency
    - Line Items (product/service name, quantity, unit price, total)

    Format the output as a valid JSON object:
        "invoice_number": <Invoice Number>
        "date": <Date>
        "due_date": <Due Date>
        "total_amount": <Total Amount>
        "tax": <Tax Amount>
        "vendor_name": <Vendor Name>
        "vendor_address": <Vendor Address>
        "account_number": <Bank Account>
        "bic": <BIC>
        "iban": <IBAN>
        "payment_terms": <Payment Terms>
        "currency": <Currency>
        "line_items": [(product_name, quantity, unit_price, total), ...]

    If you cannot find certain information, use null for those fields.
    
    INVOICE TEXT:
    {state["invoice_text"]}
    """
    
    try:
        # Generate content with Gemini
        response = model.generate_content(prompt)
        
        # Process response to extract JSON
        response_text = response.text
        
        # Find JSON in the response - handles cases where model might add explanations
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            invoice_data = json.loads(json_str)
            
            # Update state with extracted data
            return {
                "messages": [{"role": "assistant", "content": f"Successfully extracted invoice data"}],
                "invoice_data": invoice_data
            }
        else:
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Failed to extract valid JSON from model response"
                    }
                ],
                "error": "Invalid JSON format in response"
            }
    
    except Exception as e:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Error extracting invoice data: {str(e)}"
                }
            ],
            "error": str(e)
        }


# Validate and clean the extracted data
def validate_invoice_data(state: State):

    if state.get("error"):
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Validation skipped due to prior error: {state['error']}"
                }
            ]
        }
    
    invoice_data = state.get("invoice_data", {})
    
    # Add validation logic here, for example:
    validation_messages = []
    
    # Check if essential fields are present
    if not invoice_data.get("invoice_number"):
        validation_messages.append("Warning: Invoice number not found")
    
    if not invoice_data.get("total_amount"):
        validation_messages.append("Warning: Total amount not found")
    
    if not invoice_data.get("date"):
        validation_messages.append("Warning: Invoice date not found")
    
    # Format validation messages
    if validation_messages:
        validation_text = "\n".join(validation_messages)
        return {"messages": [{"role": "assistant", "content": f"Validation results:\n{validation_text}"}]}
    else:
        return {"messages": [{"role": "assistant", "content": "Validation successful: All required fields are present"}]}


# Format results for display
def format_results(state: State):

    if state.get("error"):
        return {"messages": [{"role": "assistant", "content": f"Cannot format results due to error: {state['error']}"}]}
    
    invoice_data = state.get("invoice_data", {})
    
    # Create a formatted summary
    summary = [
        "## Invoice Summary",
        f"**Invoice Number**: {invoice_data.get('invoice_number', 'Not found')}",
        f"**Date**: {invoice_data.get('date', 'Not found')}",
        f"**Due Date**: {invoice_data.get('due_date', 'Not found')}",
        f"**Total Amount**: {invoice_data.get('total_amount', 'Not found')} {invoice_data.get('currency', '')}",
        f"**Tax Amount**: {invoice_data.get('tax_amount', 'Not found')} {invoice_data.get('currency', '')}",
        "",
        "## Vendor Information",
        f"**Vendor**: {invoice_data.get('vendor_name', 'Not found')}",
        f"**Address**: {invoice_data.get('vendor_address', 'Not found')}",
        "",
        "## Payment Information",
        f"**Bank Account**: {invoice_data.get('bank_account', 'Not found')}",
        f"**BIC**: {invoice_data.get('bic', 'Not found')}",
        f"**IBAN**: {invoice_data.get('iban', 'Not found')}",
        f"**Payment Terms**: {invoice_data.get('payment_terms', 'Not found')}",
    ]
    
    # Add line items if available
    line_items = invoice_data.get("line_items", [])
    if line_items:
        summary.append("")
        summary.append("## Line Items")
        for i, item in enumerate(line_items, 1):
            summary.append(
                f"{i}. **{item.get('description', 'Item')}**: {item.get('quantity', '')} x {item.get('unit_price', '')} = {item.get('total', '')}"
            )
    
    formatted_summary = "\n".join(summary)
    return {"messages": [{"role": "assistant", "content": formatted_summary}]}


# Build the graph
def build_invoice_graph():

    # Create a new graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("extract", extract_invoice_data)
    workflow.add_node("validate", validate_invoice_data)
    workflow.add_node("format", format_results)
    
    # Add edges
    workflow.add_edge("extract", "validate")
    workflow.add_edge("validate", "format")
    workflow.add_edge("format", END)
    
    # Set entry point
    workflow.set_entry_point("extract")
    
    # Compile the graph
    return workflow.compile()


# Main function
def process_invoice(invoice_text: str):

    # Initialize the graph
    invoice_graph = build_invoice_graph()
    
    # Set initial state
    initial_state = {
        "messages": [],
        "invoice_text": invoice_text,
        "invoice_data": None,
        "error": None
    }
    
    # Execute the graph
    result = invoice_graph.invoke(initial_state)
    
    # Return the result
    return {
        "messages": result["messages"],
        "invoice_data": result["invoice_data"],
        "error": result.get("error")
    }


# Example usage
if __name__ == "__main__":

    # Example invoice text
    # sample_invoice = """
    # INVOICE
    
    # Invoice Number: INV-2025-0042
    # Date: 24/04/2025
    # Due Date: 08/05/2025
    
    # Vendor: TechSupplies Ltd
    # Address: 123 Tech Lane, Innovation District, London, UK
    
    # Bill To:
    # Acme Corporation
    # 789 Business Ave
    # Enterprise City, EC 54321
    
    # Payment Details:
    # Bank Account: 78901234
    # BIC: ABCDEFGH
    # IBAN: GB29 NWBK 6016 1331 9268 19
    # Payment Terms: Net 14 days
    
    # Item Description                Quantity    Unit Price    Amount
    # ---------------------------------------------------------------
    # Premium Cloud Storage           12          €99.00        €1,188.00
    # Technical Support Hours         5           €75.00        €375.00
    # Software License Renewal        1           €599.00       €599.00
    # ---------------------------------------------------------------
    # Subtotal                                                 €2,162.00
    # VAT (20%)                                                €432.40
    # ---------------------------------------------------------------
    # Total (EUR)                                             €2,594.40
    # """

    sample_invoice = process_pdf('invoice_ENG.pdf')

    result = process_invoice(sample_invoice)
    
    # Print formatted messages - note the change in how we access message attributes
    for message in result["messages"]:
        # Access content directly as an attribute, not using dictionary syntax
        print(f"Message: {message.content}")
    
    # Print raw JSON data
    print("\nExtracted JSON Data:")
    print(json.dumps(result["invoice_data"], indent=2))

