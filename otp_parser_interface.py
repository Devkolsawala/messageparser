#!/usr/bin/env python3
"""
OTP Message Parser Interface
A flexible script that can parse single OTP messages or CSV files
and always outputs results in JSON format.
"""

import pandas as pd
import json
import sys
import os
import argparse
from typing import Dict, List, Optional
import time
from pathlib import Path

# Import the OTPMessageParser class (assuming it's in the same directory or installed as a module)
try:
    from parsing import OTPMessageParser
except ImportError:
    print("Error: Could not import OTPMessageParser. Make sure the parser.py file is in the same directory.")
    sys.exit(1)


class OTPParserInterface:
    def __init__(self):
        self.parser = OTPMessageParser()
        
    def parse_single_message(self, message: str, sender_name: str = "", output_file: str = None) -> Dict:
        """
        Parse a single OTP message and return results in JSON format
        
        Args:
            message (str): The OTP message text
            sender_name (str): Optional sender name
            output_file (str): Optional output file path for JSON
            
        Returns:
            Dict: Parsed results in JSON format
        """
        print("Parsing single OTP message...")
        
        # Parse the message
        result = self.parser.parse_single_message(message, sender_name)
        
        # Format result for JSON output
        json_result = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'parsing_type': 'single_message',
                'parser_version': '1.0'
            },
            'input': {
                'message': message,
                'sender_name': sender_name
            },
            'parsed_data': {
                'otp_code': result['otp_code'],
                'company_service': result['company_name'],
                'purpose_action': result['purpose'],
                'validity_duration': f"{result['expiry_info']['duration']} {result['expiry_info']['unit']}" if result['expiry_info'] else None,
                'expiry_full_text': result['expiry_info']['full_text'] if result['expiry_info'] else None,
                'security_warnings': result['security_warnings'],
                'reference_id': result['reference_id'],
                'phone_number': result['phone_number'],
                'account_info': result['account_info'],
                'sender_name': result['sender_name']
            },
            'extraction_success': {
                'otp_extracted': result['otp_code'] is not None,
                'company_identified': result['company_name'] is not None,
                'purpose_identified': result['purpose'] is not None,
                'expiry_found': result['expiry_info'] is not None,
                'security_warnings_found': len(result['security_warnings']) > 0,
                'reference_id_found': result['reference_id'] is not None
            }
        }
        
        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_result, f, indent=2, ensure_ascii=False)
                print(f"Results saved to: {output_file}")
            except Exception as e:
                print(f"Error saving JSON file: {e}")
        
        return json_result
    
    def parse_csv_file(self, input_file: str, output_file: str = None) -> Dict:
        """
        Parse CSV file containing OTP messages and return results in JSON format
        
        Args:
            input_file (str): Path to the CSV file
            output_file (str): Optional output file path for JSON
            
        Returns:
            Dict: Parsed results in JSON format
        """
        print(f"Parsing CSV file: {input_file}")
        
        # Validate input file
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Use the original parser's CSV processing method
        try:
            # Process CSV and get DataFrame
            df = self.parser.parse_csv_file(input_file, output_file=None, export_format='csv')
            
            if df is None:
                raise ValueError("Failed to parse CSV file")
            
            # Convert DataFrame to JSON format
            json_result = self._dataframe_to_json(df, input_file)
            
            # Determine output file if not specified
            if output_file is None:
                base_name = Path(input_file).stem
                output_file = f"{base_name}_parsed_otp_results.json"
            
            # Save JSON output
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_result, f, indent=2, ensure_ascii=False)
                print(f"\n✅ JSON results saved to: {output_file}")
            except Exception as e:
                print(f"Error saving JSON file: {e}")
            
            return json_result
            
        except Exception as e:
            print(f"Error processing CSV file: {e}")
            raise
    
    def _dataframe_to_json(self, df: pd.DataFrame, input_file: str) -> Dict:
        """Convert DataFrame results to structured JSON format"""
        
        total_messages = len(df)
        
        # Calculate statistics
        stats = {
            'total_messages': int(total_messages),
            'otp_codes_extracted': int(df['OTP_Code'].notna().sum()),
            'companies_identified': int(df['Company_Service'].notna().sum()),
            'purposes_identified': int(df['Purpose_Action'].notna().sum()),
            'expiry_info_found': int(df['Validity_Duration'].notna().sum()),
            'security_warnings_found': int(df['Security_Warnings'].notna().sum()),
            'reference_ids_found': int(df['Reference_ID'].notna().sum()),
        }
        
        # Calculate accuracy metrics
        accuracy_metrics = self.parser.calculate_accuracy_metrics(df)
        
        # Convert DataFrame to records
        records = []
        for _, row in df.iterrows():
            record = {
                'original_index': int(row['Original_Row_Index']) if pd.notna(row['Original_Row_Index']) else None,
                'otp_code': str(row['OTP_Code']) if pd.notna(row['OTP_Code']) else None,
                'company_service': str(row['Company_Service']) if pd.notna(row['Company_Service']) else None,
                'purpose_action': str(row['Purpose_Action']) if pd.notna(row['Purpose_Action']) else None,
                'validity_duration': str(row['Validity_Duration']) if pd.notna(row['Validity_Duration']) else None,
                'security_warnings': str(row['Security_Warnings']) if pd.notna(row['Security_Warnings']) else None,
                'reference_id': str(row['Reference_ID']) if pd.notna(row['Reference_ID']) else None,
                'phone_number': str(row['Phone_Number']) if pd.notna(row['Phone_Number']) else None,
                'account_info': str(row['Account_Info']) if pd.notna(row['Account_Info']) else None,
                'sender_name': str(row['Sender_Name']) if pd.notna(row['Sender_Name']) else None,
                'full_message': str(row['Full_Message']) if pd.notna(row['Full_Message']) else None,
            }
            records.append(record)
        
        # Create distribution analysis
        distribution_analysis = {
            'company_distribution': {str(k): int(v) for k, v in df['Company_Service'].value_counts().head(20).items() if pd.notna(k)},
            'purpose_distribution': {str(k): int(v) for k, v in df['Purpose_Action'].value_counts().items() if pd.notna(k)},
            'expiry_distribution': {str(k): int(v) for k, v in df['Validity_Duration'].value_counts().items() if pd.notna(k)},
        }
        
        # Create final JSON structure
        json_result = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'input_file': input_file,
                'parsing_type': 'csv_batch',
                'parser_version': '1.0',
                'description': 'Parsed OTP SMS messages with extracted structured information'
            },
            'summary_statistics': stats,
            'accuracy_metrics': accuracy_metrics,
            'distribution_analysis': distribution_analysis,
            'parsed_messages': records
        }
        
        return json_result
    
    def interactive_mode(self):
        """Run the parser in interactive mode"""
        print("\n" + "="*70)
        print("OTP MESSAGE PARSER - INTERACTIVE MODE")
        print("="*70)
        print("Choose your input method:")
        print("1. Parse a single OTP message")
        print("2. Parse a CSV file with OTP messages")
        print("3. Exit")
        
        while True:
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == '1':
                self._handle_single_message()
            elif choice == '2':
                self._handle_csv_file()
            elif choice == '3':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    def _handle_single_message(self):
        """Handle single message parsing in interactive mode"""
        print("\n" + "-"*50)
        print("SINGLE MESSAGE PARSING")
        print("-"*50)
        
        message = input("Enter the OTP message: ").strip()
        if not message:
            print("No message provided.")
            return
        
        sender = input("Enter sender name (optional): ").strip()
        
        save_to_file = input("Save results to file? (y/n): ").lower().strip()
        output_file = None
        
        if save_to_file == 'y':
            output_file = input("Enter output file path (or press Enter for auto-naming): ").strip()
            if not output_file:
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                output_file = f"single_otp_parsed_{timestamp}.json"
        
        try:
            result = self.parse_single_message(message, sender, output_file)
            
            print("\n" + "="*50)
            print("PARSING RESULTS")
            print("="*50)
            
            parsed_data = result['parsed_data']
            print(f"OTP Code: {parsed_data['otp_code']}")
            print(f"Company/Service: {parsed_data['company_service']}")
            print(f"Purpose: {parsed_data['purpose_action']}")
            print(f"Validity: {parsed_data['validity_duration']}")
            print(f"Security Warnings: {len(parsed_data['security_warnings'])} found")
            print(f"Reference ID: {parsed_data['reference_id']}")
            print(f"Phone Number: {parsed_data['phone_number']}")
            
            if not output_file:
                print("\nFull JSON Output:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
        except Exception as e:
            print(f"Error parsing message: {e}")
    
    def _handle_csv_file(self):
        """Handle CSV file parsing in interactive mode"""
        print("\n" + "-"*50)
        print("CSV FILE PARSING")
        print("-"*50)
        
        input_file = input("Enter the path to your CSV file: ").strip().strip('"')
        if not input_file:
            print("No file path provided.")
            return
        
        output_file = input("Enter output JSON file path (or press Enter for auto-naming): ").strip()
        if not output_file:
            base_name = Path(input_file).stem
            output_file = f"{base_name}_parsed_results.json"
        
        try:
            result = self.parse_csv_file(input_file, output_file)
            
            print("\n" + "="*50)
            print("PARSING SUMMARY")
            print("="*50)
            
            stats = result['summary_statistics']
            accuracy = result['accuracy_metrics']
            
            print(f"Total messages processed: {stats['total_messages']:,}")
            print(f"OTP codes extracted: {stats['otp_codes_extracted']:,} ({accuracy['otp_extraction_accuracy']}%)")
            print(f"Companies identified: {stats['companies_identified']:,} ({accuracy['company_identification_accuracy']}%)")
            print(f"Purposes identified: {stats['purposes_identified']:,} ({accuracy['purpose_identification_accuracy']}%)")
            print(f"Overall completeness: {accuracy['overall_completeness_score']}%")
            
            # Show top companies
            print("\nTop 5 Companies:")
            company_dist = result['distribution_analysis']['company_distribution']
            for i, (company, count) in enumerate(list(company_dist.items())[:5], 1):
                print(f"{i}. {company}: {count:,} messages")
                
        except Exception as e:
            print(f"Error processing CSV file: {e}")


def create_command_line_interface():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="OTP Message Parser - Extract structured data from OTP SMS messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse a single message
  python otp_parser_interface.py -m "123456 is your OTP for Dream11 login" -s "DM-DREAM11" -o result.json
  
  # Parse a CSV file
  python otp_parser_interface.py -f messages.csv -o parsed_results.json
  
  # Run in interactive mode
  python otp_parser_interface.py
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('-m', '--message', type=str, help='Single OTP message to parse')
    input_group.add_argument('-f', '--file', type=str, help='CSV file path containing OTP messages')
    
    # Optional arguments
    parser.add_argument('-s', '--sender', type=str, default="", help='Sender name (for single message mode)')
    parser.add_argument('-o', '--output', type=str, help='Output JSON file path')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress progress output')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON output to console')
    
    return parser


def main():
    """Main function to handle different execution modes"""
    
    # Create argument parser
    arg_parser = create_command_line_interface()
    args = arg_parser.parse_args()
    
    # Initialize the OTP parser interface
    otp_interface = OTPParserInterface()
    
    try:
        # Command line mode with message
        if args.message:
            if not args.quiet:
                print("Command Line Mode - Single Message")
                print("="*50)
            
            result = otp_interface.parse_single_message(
                args.message, 
                args.sender or "", 
                args.output
            )
            
            if args.pretty:
                print("\nParsed Results:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if not args.output and not args.pretty:
                # Output JSON to stdout for piping
                print(json.dumps(result, ensure_ascii=False))
        
        # Command line mode with CSV file
        elif args.file:
            if not args.quiet:
                print("Command Line Mode - CSV File")
                print("="*50)
            
            result = otp_interface.parse_csv_file(args.file, args.output)
            
            if args.pretty:
                # Show summary for large files
                stats = result['summary_statistics']
                accuracy = result['accuracy_metrics']
                
                print(f"\nProcessing Summary:")
                print(f"Messages processed: {stats['total_messages']:,}")
                print(f"OTP extraction accuracy: {accuracy['otp_extraction_accuracy']}%")
                print(f"Overall completeness: {accuracy['overall_completeness_score']}%")
            
            if not args.output and not args.pretty:
                # Output JSON to stdout (be careful with large files)
                if result['summary_statistics']['total_messages'] > 1000:
                    print("Large file detected. Use --output flag to save to file instead of printing to console.")
                else:
                    print(json.dumps(result, ensure_ascii=False))
        
        # Interactive mode
        else:
            otp_interface.interactive_mode()
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


class OTPBatchProcessor:
    """Additional utility class for batch processing multiple messages"""
    
    def __init__(self):
        self.parser = OTPMessageParser()
    
    def parse_message_list(self, messages: List[Dict], output_file: str = None) -> Dict:
        """
        Parse a list of message dictionaries
        
        Args:
            messages (List[Dict]): List of messages with 'message' and optional 'sender_name' keys
            output_file (str): Optional output file path
            
        Returns:
            Dict: Parsed results in JSON format
        """
        
        print(f"Processing {len(messages)} messages...")
        
        parsed_results = []
        
        for i, msg_data in enumerate(messages):
            message = msg_data.get('message', '')
            sender = msg_data.get('sender_name', '')
            
            result = self.parser.parse_single_message(message, sender)
            
            # Format for JSON
            formatted_result = {
                'message_index': i,
                'otp_code': result['otp_code'],
                'company_service': result['company_name'],
                'purpose_action': result['purpose'],
                'validity_duration': f"{result['expiry_info']['duration']} {result['expiry_info']['unit']}" if result['expiry_info'] else None,
                'security_warnings': result['security_warnings'],
                'reference_id': result['reference_id'],
                'phone_number': result['phone_number'],
                'account_info': result['account_info'],
                'sender_name': result['sender_name'],
                'full_message': result['raw_message']
            }
            
            parsed_results.append(formatted_result)
        
        # Calculate summary statistics
        total_count = len(parsed_results)
        stats = {
            'total_messages': total_count,
            'otp_codes_extracted': sum(1 for r in parsed_results if r['otp_code']),
            'companies_identified': sum(1 for r in parsed_results if r['company_service']),
            'purposes_identified': sum(1 for r in parsed_results if r['purpose_action']),
            'expiry_info_found': sum(1 for r in parsed_results if r['validity_duration']),
            'security_warnings_found': sum(1 for r in parsed_results if r['security_warnings']),
        }
        
        # Create final JSON structure
        json_result = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'parsing_type': 'batch_processing',
                'parser_version': '1.0'
            },
            'summary_statistics': stats,
            'parsed_messages': parsed_results
        }
        
        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_result, f, indent=2, ensure_ascii=False)
                print(f"Batch results saved to: {output_file}")
            except Exception as e:
                print(f"Error saving JSON file: {e}")
        
        return json_result


# Example usage functions
def example_single_message():
    """Example of parsing a single message"""
    parser_interface = OTPParserInterface()
    
    sample_message = "676653 is the OTP for your Dream11 account. Do not share this with anyone. Dream11 will never call or message asking for OTP."
    sample_sender = "DM-DREAM11"
    
    result = parser_interface.parse_single_message(sample_message, sample_sender)
    
    print("Example Single Message Parsing:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def example_batch_processing():
    """Example of batch processing multiple messages"""
    batch_processor = OTPBatchProcessor()
    
    sample_messages = [
        {
            'message': "676653 is the OTP for your Dream11 account. Do not share this with anyone.",
            'sender_name': "DM-DREAM11"
        },
        {
            'message': "Your OTP for Meesho login is 810671 and is valid for 30 mins.",
            'sender_name': "DM-MEESHO"
        },
        {
            'message': "Paytm OTP: 955980. Never share with anyone. ID: asK2GTt2i",
            'sender_name': "VM-PAYTM"
        }
    ]
    
    result = batch_processor.parse_message_list(sample_messages)
    
    print("Example Batch Processing:")
    print(json.dumps(result['summary_statistics'], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()