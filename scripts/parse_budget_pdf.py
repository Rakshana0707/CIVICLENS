import os
import glob
import pandas as pd
import pdfplumber
import re

RAW_DIR = os.path.join("data", "raw", "budget")
PROCESSED_DIR = os.path.join("data", "processed", "budget")

def extract_budget_data(pdf_path):
    print(f"Processing: {pdf_path}")
    all_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract tables with standard pdfplumber settings
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                    
                    # Convert to DataFrame for easier manipulation
                    df = pd.DataFrame(table)
                    
                    # Basic cleaning: remove completely empty rows/cols
                    df.dropna(how='all', inplace=True)
                    df.dropna(axis=1, how='all', inplace=True)
                    
                    if df.empty:
                        continue
                        
                    # Clean text: remove newlines and extra spaces
                    df = df.applymap(lambda x: str(x).strip().replace('\n', ' ') if pd.notnull(x) else "")
                    
                    # Add metadata
                    df['source_page'] = page_num + 1
                    
                    all_data.append(df)
                    
        if all_data:
            # Combine all tables found in the PDF
            final_df = pd.concat(all_data, ignore_index=True)
            return final_df
        else:
            print(f"No tables found in {pdf_path}")
            return None
            
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return None

def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    pdf_files = glob.glob(os.path.join(RAW_DIR, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {RAW_DIR}.")
        print("Please place the official Demands for Grants PDFs there once the TN portal is accessible.")
        return
        
    for pdf_file in pdf_files:
        base_name = os.path.basename(pdf_file)
        csv_name = base_name.replace('.pdf', '_raw_extracted.csv')
        csv_path = os.path.join(PROCESSED_DIR, csv_name)
        
        extracted_df = extract_budget_data(pdf_file)
        if extracted_df is not None:
            # Output the raw extracted table. 
            # Further semantic cleaning (identifying headers, cleaning Tamil/English) 
            # will be implemented once actual data structure is verified.
            extracted_df.to_csv(csv_path, index=False, header=False)
            print(f"Successfully extracted {len(extracted_df)} rows to {csv_path}")

if __name__ == "__main__":
    main()
