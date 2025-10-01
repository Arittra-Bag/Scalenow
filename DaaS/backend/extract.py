import pandas as pd
import os

def extract_from_excel(file_path):
    """Extract data from an Excel file."""
    return pd.read_excel(file_path)

def extract_from_folder(folder_path):
    """Extract data from files in a folder and its subfolders."""
    all_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            all_files.append(full_path)
    return all_files

# Example usage
if __name__ == "__main__":
    excel_data = extract_from_excel("data/sample.xlsx")
    print("Excel Data Extracted:")
    print(excel_data.head())

    folder_files = extract_from_folder("data/folder_input")
    print("Files Extracted from Folder:")
    print(folder_files)
