from extract import extract_from_excel, extract_from_folder
from transform import transform_excel_data, transform_file_list
from load import load_to_csv, save_file_list

def main():
    # Extract
    excel_data = extract_from_excel("data/sample.xlsx")
    folder_files = extract_from_folder("data/folder_input")

    # Transform
    transformed_excel_data = transform_excel_data(excel_data)
    transformed_file_list = transform_file_list(folder_files)

    # Load
    load_to_csv(transformed_excel_data, "output/transformed.csv")
    save_file_list(transformed_file_list, "output/files_list.txt")

    print("ETL process completed.")

if __name__ == "__main__":
    main()
