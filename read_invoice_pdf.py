"""
Simple Invoice Parser using Google Gemini's PDF processing capabilities

This script extracts structured information from invoice PDFs using Google's Gemini model
with native PDF processing and validates the extracted data using custom validation functions.
"""

import os
import json
import re
import datetime
import io
from typing import Dict, Any, Optional, Callable, TypeVar
import logging
from pathlib import Path

# For Gemini API with latest SDK (google-genai)
from google import genai
from google.genai import types

# Read your API key from the environment variable or set it manually
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Type for validation functions
T = TypeVar('T')
ValidationFunc = Callable[[Any], tuple[bool, Optional[str], Optional[T]]]

class InvoiceParser:
    """Main class for parsing invoices using Gemini's native PDF processing."""
    
    def __init__(self, api_key: str):
        """
        Initialize the invoice parser.
        
        Args:
            api_key: Google API key for Gemini
        """
        self.api_key = api_key
        self._setup_gemini()
        self.validator = FieldValidator()
    
    def _setup_gemini(self):
        """Configure the Gemini API with credentials."""
        try:
            # Set up the API client using new SDK format
            self.client = genai.Client(api_key=self.api_key)
            # Set model name
            self.model_name = "gemini-2.0-flash"
            logger.info("Gemini API configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            raise
    
    def process_invoice(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process an invoice PDF and extract structured information.
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            Dict with structured invoice data
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Step 1: Process PDF with Gemini
            extracted_data = self._process_pdf_with_gemini(pdf_path)
            
            # Step 2: Validate extracted fields
            validated_data, validation_errors = self._validate_fields(extracted_data)
            
            # Step 3: Log validation errors as warnings
            for field, error in validation_errors.items():
                logger.warning(f"Validation error for {field}: {error}")
            
            # Return validated data
            return validated_data
            
        except Exception as e:
            logger.error(f"Error processing invoice: {e}")
            raise
    
    def _process_pdf_with_gemini(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process the PDF directly with Gemini instead of extracting text first.
        This leverages Gemini's native PDF processing capabilities.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted data
        """
        logger.info(f"Processing PDF with Gemini: {pdf_path}")
        
        try:
            # Read the PDF file
            pdf_path = Path(pdf_path)
            pdf_data = pdf_path.read_bytes()
            
            # Check file size to determine upload method
            file_size_mb = len(pdf_data) / (1024 * 1024)  # Size in MB
            
            # Prepare prompt for the model
            prompt = """
            Extract the following information from this invoice and return it as a JSON object. 
            If a piece of information is not found, set the value to null.
            
            Information to extract:
            - invoice_number
            - date (invoice date)
            - due_date
            - total_amount (numeric)
            - tax_amount (numeric)
            - taxfree_amount (numeric)
            - vendor_name
            - vendor_address
            - account_number
            - bic
            - iban
            - reference_number
            - payment_terms
            - currency
            - line_items (array of items with product_name, quantity, unit_price, total)
            
            Return ONLY the JSON object without any additional explanation.
            """
            
            if file_size_mb < 20:
                # For smaller files, use direct processing
                logger.info("Using direct PDF processing")
                
                # Create content with PDF and prompt
                contents = [
                    types.Part.from_bytes(data=pdf_data, mime_type='application/pdf'),
                    prompt
                ]
                
                # Generate content with the updated SDK format
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
            else:
                # For larger files, use the File API
                logger.info("Using File API for large PDF")
                
                # Upload the file with new SDK format
                file_io = io.BytesIO(pdf_data)
                uploaded_file = self.client.files.upload(
                    file=file_io,
                    config=dict(mime_type='application/pdf')
                )
                
                # Generate content with the uploaded file
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
            
            # Process the response - extract JSON
            try:
                # Try parsing directly if response contains valid JSON
                extracted_data = json.loads(response.text)
            except json.JSONDecodeError:
                # Try to extract JSON from text content if direct parsing fails
                json_match = re.search(r'```(?:json)?\s*(.*?)```', response.text, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(1)
                    extracted_data = json.loads(json_str)
                else:
                    logger.warning("Could not extract JSON from response. Using raw text.")
                    extracted_data = self._get_empty_invoice_structure()
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error processing PDF with Gemini: {e}")
            # Return empty structure in case of failure
            return self._get_empty_invoice_structure()
    
    def _validate_fields(self, extracted_data: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Validate all extracted fields using the validator.
        
        Args:
            extracted_data: Dictionary with extracted invoice data
            
        Returns:
            Tuple of (validated_data, validation_errors)
        """
        logger.info("Validating extracted fields")
        
        validated_data = {}
        validation_errors = {}
        
        # Process each field with its corresponding validator
        for field, value in extracted_data.items():
            if field == "line_items" and isinstance(value, list):
                # Handle line items separately (as they're a list of dicts)
                validated_line_items = []
                line_item_errors = []
                
                for i, item in enumerate(value):
                    item_validated = {}
                    item_errors = {}
                    
                    # Validate each field in the line item
                    for item_field, item_value in item.items():
                        validator_name = f"line_item_{item_field}"
                        if hasattr(self.validator, validator_name):
                            validator = getattr(self.validator, validator_name)
                            valid, error, validated_value = validator(item_value)
                            item_validated[item_field] = validated_value
                            if not valid:
                                item_errors[item_field] = error
                        else:
                            # No validator, keep as is
                            item_validated[item_field] = item_value
                    
                    validated_line_items.append(item_validated)
                    if item_errors:
                        line_item_errors.append((i, item_errors))
                
                validated_data["line_items"] = validated_line_items
                if line_item_errors:
                    validation_errors["line_items"] = line_item_errors
                
            else:
                # Regular field validation
                validator_name = field
                if hasattr(self.validator, validator_name):
                    validator = getattr(self.validator, validator_name)
                    valid, error, validated_value = validator(value)
                    validated_data[field] = validated_value
                    if not valid:
                        validation_errors[field] = error
                else:
                    # No validator available, keep as is
                    validated_data[field] = value
        
        return validated_data, validation_errors
    
    def _get_empty_invoice_structure(self) -> Dict[str, Any]:
        """Return an empty invoice structure with all fields set to null."""
        return {
            "invoice_number": None,
            "date": None,
            "due_date": None,
            "total_amount": None,
            "tax_amount": None,
            "taxfree_amount": None,
            "vendor_name": None,
            "vendor_address": None,
            "account_number": None,
            "bic": None,
            "iban": None,
            "reference_number": None,
            "payment_terms": None,
            "currency": None,
            "line_items": []
        }


class FieldValidator:
    """Class containing validation functions for different invoice fields."""
    
    def invoice_number(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate invoice number.
        
        Args:
            value: The invoice number to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            # Convert to string
            value_str = str(value).strip()
            
            if not value_str:
                return False, "Invoice number is empty", None
            
            # Basic validation - could be enhanced with specific patterns
            return True, None, value_str
        except Exception as e:
            return False, f"Invalid invoice number: {e}", None
    
    def date(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate and normalize date formats.
        Handles various formats including DD.MM.YYYY, YYYY-MM-DD, etc.
        
        Args:
            value: The date to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            value_str = str(value).strip()
            if not value_str:
                return False, "Date is empty", None
            
            # Try different date formats
            date_formats = [
                "%d.%m.%Y",  # 31.12.2023
                "%Y-%m-%d",  # 2023-12-31
                "%d/%m/%Y",  # 31/12/2023
                "%m/%d/%Y",  # 12/31/2023
                "%d-%m-%Y",  # 31-12-2023
                "%d.%m.%y",  # 31.12.23
                "%Y.%m.%d",  # 2023.12.31
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.datetime.strptime(value_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                return False, f"Could not parse date '{value_str}'", None
            
            # Return normalized format
            return True, None, parsed_date.strftime("%d.%m.%Y")
        except Exception as e:
            return False, f"Invalid date: {e}", None
    
    def due_date(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate due date - uses the same logic as the date validator.
        
        Args:
            value: The due date to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        # Reuse the date validator
        return self.date(value)
    
    def total_amount(self, value: Any) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Validate total amount as a number.
        
        Args:
            value: The amount to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            # Handle different formats of numbers
            if isinstance(value, str):
                # Replace comma with dot for decimal separator
                value = value.replace(',', '.')
                # Remove any currency symbols or spaces
                value = re.sub(r'[^\d.-]', '', value)
            
            amount = float(value)
            
            if amount < 0:
                return False, "Total amount cannot be negative", None
            
            return True, None, round(amount, 2)
        except (ValueError, TypeError) as e:
            return False, f"Invalid total amount: {e}", None
    
    def tax_amount(self, value: Any) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Validate tax amount as a number.
        
        Args:
            value: The tax amount to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        # Reuse the total_amount validator
        return self.total_amount(value)
    
    def taxfree_amount(self, value: Any) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Validate tax-free amount as a number.
        
        Args:
            value: The tax-free amount to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        # Reuse the total_amount validator
        return self.total_amount(value)
    
    def account_number(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate Finnish account number.
        
        Args:
            value: The account number to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            value_str = str(value).strip()
            if not value_str:
                return False, "Account number is empty", None
            
            # Finnish account number format: XXXXXX-XXXXXXX
            if re.match(r'^\d{6}-\d{7,8}$', value_str):
                return True, None, value_str
            
            return False, "Invalid Finnish account number format", None
        except Exception as e:
            return False, f"Invalid account number: {e}", None
    
    def bic(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate BIC (Bank Identifier Code).
        
        Args:
            value: The BIC to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            value_str = str(value).strip().upper()
            if not value_str:
                return False, "BIC is empty", None
            
            # BIC format: 8 or 11 alphanumeric characters
            # First 4 characters: bank code (letters)
            # Next 2 characters: country code (letters)
            # Next 2 characters: location code (alphanumeric)
            # Optional 3 characters: branch code (alphanumeric)
            if re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', value_str):
                return True, None, value_str
            
            return False, "Invalid BIC format", None
        except Exception as e:
            return False, f"Invalid BIC: {e}", None
    
    def iban(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate IBAN (International Bank Account Number).
        
        Args:
            value: The IBAN to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            # Remove spaces and convert to uppercase
            value_str = str(value).replace(' ', '').upper().strip()
            if not value_str:
                return False, "IBAN is empty", None
            
            # Finnish IBAN format validation
            if value_str.startswith('FI'):
                # Finnish IBAN is FI followed by 16 digits
                if re.match(r'^FI\d{16}$', value_str):
                    # Format with spaces for readability
                    formatted_iban = ' '.join([value_str[i:i+4] for i in range(0, len(value_str), 4)])
                    return True, None, formatted_iban
            else:
                # Generic IBAN validation
                # IBAN format: 2 letter country code + 2 check digits + basic bank account number (up to 30 chars)
                if re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$', value_str):
                    # Format with spaces for readability
                    formatted_iban = ' '.join([value_str[i:i+4] for i in range(0, len(value_str), 4)])
                    return True, None, formatted_iban
            
            return False, "Invalid IBAN format", None
        except Exception as e:
            return False, f"Invalid IBAN: {e}", None
    
    def reference_number(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate Finnish reference number.
        
        Args:
            value: The reference number to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            # Remove spaces
            value_str = str(value).replace(' ', '').strip()
            if not value_str:
                return False, "Reference number is empty", None
            
            # Finnish reference number validation
            # Format: digits only, last digit is a check digit
            if re.match(r'^\d{4,25}$', value_str):
                # For simplicity, we'll just check the format
                # In a real implementation, you'd validate the check digit
                # Format with spaces for readability (groups of 5)
                formatted_ref = ' '.join([value_str[max(0, i-5):i] for i in range(len(value_str), 0, -5)][::-1])
                return True, None, formatted_ref
            
            return False, "Invalid Finnish reference number format", None
        except Exception as e:
            return False, f"Invalid reference number: {e}", None
    
    def currency(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validate currency.
        
        Args:
            value: The currency to validate
            
        Returns:
            (valid, error_message, validated_value)
        """
        if value is None:
            return True, None, None
        
        try:
            value_str = str(value).strip().lower()
            if not value_str:
                return False, "Currency is empty", None
            
            # List of common currencies
            currencies = {
                "euro": "EUR",
                "eur": "EUR",
                "€": "EUR",
                "usd": "USD",
                "dollar": "USD",
                "$": "USD",
                "gbp": "GBP",
                "pound": "GBP",
                "£": "GBP",
                # Add more as needed
            }
            
            # Try to normalize the currency
            if value_str in currencies:
                return True, None, currencies[value_str]
            
            # If it's a 3-letter code, check if it's valid
            if re.match(r'^[A-Za-z]{3}$', value_str):
                return True, None, value_str.upper()
            
            return True, None, value_str  # Accept as is if we can't normalize
        except Exception as e:
            return False, f"Invalid currency: {e}", None
    
    def line_item_product_name(self, value: Any) -> tuple[bool, Optional[str], Optional[str]]:
        """Validate product name in line items."""
        if value is None:
            return True, None, None
        
        try:
            value_str = str(value).strip()
            if not value_str:
                return False, "Product name is empty", None
            
            return True, None, value_str
        except Exception as e:
            return False, f"Invalid product name: {e}", None
    
    def line_item_quantity(self, value: Any) -> tuple[bool, Optional[str], Optional[float]]:
        """Validate quantity in line items."""
        if value is None:
            return True, None, None
        
        try:
            # Handle string representations
            if isinstance(value, str):
                value = value.replace(',', '.')
                value = re.sub(r'[^\d.-]', '', value)
            
            quantity = float(value)
            
            if quantity < 0:
                return False, "Quantity cannot be negative", None
            
            # If it's a whole number, convert to int
            if quantity.is_integer():
                return True, None, int(quantity)
            else:
                return True, None, round(quantity, 2)
        except (ValueError, TypeError) as e:
            return False, f"Invalid quantity: {e}", None
    
    def line_item_unit_price(self, value: Any) -> tuple[bool, Optional[str], Optional[float]]:
        """Validate unit price in line items."""
        # Reuse the total_amount validator
        return self.total_amount(value)
    
    def line_item_total(self, value: Any) -> tuple[bool, Optional[str], Optional[float]]:
        """Validate total price in line items."""
        # Reuse the total_amount validator
        return self.total_amount(value)


# Example usage
def main():
    """Example usage of the InvoiceParser."""
    # Replace with your actual API key
    api_key = os.environ.get("GEMINI_API_KEY", "your_api_key_here")
    
    # Create parser
    parser = InvoiceParser(api_key)
    
    # Process an invoice (replace with your PDF path)
    invoice_data = parser.process_invoice("Invoice_ENG.pdf")
    
    # Pretty print the result
    print(json.dumps(invoice_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

