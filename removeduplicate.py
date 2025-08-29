import pandas as pd
import time
from pathlib import Path

def remove_duplicate_messages(input_file, output_file=None, message_column=None):
    """
    Remove duplicate text messages from CSV file and return counts
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str, optional): Path to output CSV file. If None, adds '_unique' to input filename
        message_column (str, optional): Name of the message column. If None, will try common names
    
    Returns:
        dict: Dictionary with original count, unique count, and duplicates removed count
    """
    
    print(f"Loading CSV file: {input_file}")
    start_time = time.time()
    
    try:
        # Read CSV in chunks to handle large files efficiently
        chunk_size = 50000  # Adjust based on your system's memory
        chunks = []
        
        # First, read a small sample to identify the message column
        sample_df = pd.read_csv(input_file, nrows=5)
        
        # If message_column not specified, try to identify it automatically
        if message_column is None:
            possible_message_cols = ['message', 'text', 'content', 'body', 'msg', 'text_message']
            message_column = None
            
            for col in possible_message_cols:
                if col.lower() in [c.lower() for c in sample_df.columns]:
                    message_column = col
                    break
            
            if message_column is None:
                print("Available columns:", sample_df.columns.tolist())
                message_column = input("Please enter the name of the message column: ")
        
        print(f"Using column '{message_column}' for message text")
        
        # Read the entire file in chunks
        for chunk in pd.read_csv(input_file, chunksize=chunk_size):
            chunks.append(chunk)
        
        # Combine all chunks
        df = pd.concat(chunks, ignore_index=True)
        
        load_time = time.time() - start_time
        print(f"File loaded in {load_time:.2f} seconds")
        
        # Get original count
        original_count = len(df)
        print(f"Total messages in original file: {original_count:,}")
        
        # Remove duplicates based on message column
        print("Removing duplicates...")
        dedup_start = time.time()
        
        # Remove duplicates keeping the first occurrence
        df_unique = df.drop_duplicates(subset=[message_column], keep='first')
        
        dedup_time = time.time() - dedup_start
        print(f"Deduplication completed in {dedup_time:.2f} seconds")
        
        # Get counts
        unique_count = len(df_unique)
        duplicates_removed = original_count - unique_count
        
        # Create output filename if not provided
        if output_file is None:
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_unique{input_path.suffix}"
        
        # Save unique messages to new CSV
        print(f"Saving unique messages to: {output_file}")
        save_start = time.time()
        df_unique.to_csv(output_file, index=False)
        save_time = time.time() - save_start
        print(f"File saved in {save_time:.2f} seconds")
        
        # Print summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Original messages: {original_count:,}")
        print(f"Unique messages: {unique_count:,}")
        print(f"Duplicates removed: {duplicates_removed:,}")
        print(f"Duplicate percentage: {(duplicates_removed/original_count)*100:.2f}%")
        print(f"Total processing time: {time.time() - start_time:.2f} seconds")
        print("="*50)
        
        return {
            'original_count': original_count,
            'unique_count': unique_count,
            'duplicates_removed': duplicates_removed,
            'duplicate_percentage': (duplicates_removed/original_count)*100
        }
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

def get_message_stats_only(input_file, message_column=None):
    """
    Just get statistics without creating a new file (useful for very large files)
    """
    print(f"Analyzing CSV file: {input_file}")
    start_time = time.time()
    
    try:
        # Read a sample to identify message column
        sample_df = pd.read_csv(input_file, nrows=5)
        
        if message_column is None:
            possible_message_cols = ['message', 'text', 'content', 'body', 'msg', 'text_message']
            message_column = None
            
            for col in possible_message_cols:
                if col.lower() in [c.lower() for c in sample_df.columns]:
                    message_column = col
                    break
            
            if message_column is None:
                print("Available columns:", sample_df.columns.tolist())
                message_column = input("Please enter the name of the message column: ")
        
        # Count total rows
        total_count = sum(1 for _ in open(input_file)) - 1  # Subtract header
        print(f"Total messages: {total_count:,}")
        
        # Count unique messages using pandas
        df = pd.read_csv(input_file)
        unique_count = df[message_column].nunique()
        duplicates = total_count - unique_count
        
        print(f"Unique messages: {unique_count:,}")
        print(f"Duplicate messages: {duplicates:,}")
        print(f"Duplicate percentage: {(duplicates/total_count)*100:.2f}%")
        
        return {
            'total_count': total_count,
            'unique_count': unique_count,
            'duplicates': duplicates
        }
        
    except Exception as e:
        print(f"Error analyzing file: {str(e)}")
        return None

# Example usage
if __name__ == "__main__":
    # Replace with your actual file path
    input_csv = "D:\Dev\DA\sorted.csv"
    
    # Method 1: Remove duplicates and save to new file
    print("Choose an option:")
    print("1. Remove duplicates and create new file")
    print("2. Just analyze and show statistics")
    
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == "1":
        # Full processing - removes duplicates and saves new file
        stats = remove_duplicate_messages(
            input_file=input_csv,
            output_file=None,  # Will auto-generate filename
            message_column=None  # Will auto-detect or ask
        )
    elif choice == "2":
        # Just get statistics without creating new file
        stats = get_message_stats_only(
            input_file=input_csv,
            message_column=None
        )
    else:
        print("Invalid choice!")