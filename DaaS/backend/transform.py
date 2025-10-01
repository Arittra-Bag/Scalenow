import os

def transform_excel_data(dataframe):
    """Transform Excel data."""
    # Example: Add a new column
    dataframe["NewColumn"] = dataframe.iloc[:, 0] * 2
    return dataframe

def transform_file_list(file_list):
    """Process a list of files."""
    return [os.path.basename(file) for file in file_list]

# Example usage
if __name__ == "__main__":
    import pandas as pd

    # Example Excel data transformation
    df = pd.read_excel("data/sample.xlsx")
    transformed_data = transform_excel_data(df)
    print("Transformed Excel Data:")
    print(transformed_data.head())
