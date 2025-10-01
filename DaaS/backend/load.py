import pandas as pd
import os

def load_to_csv(dataframe, output_path):
    """Save a DataFrame to a CSV file."""
    dataframe.to_csv(output_path, index=False)

def save_file_list(file_list, output_path):
    """Save a list of file names to a text file."""
    with open(output_path, "w") as f:
        for file in file_list:
            f.write(f"{file}\n")

# Example usage
if __name__ == "__main__":
    # Save transformed Excel data
    df = pd.read_excel("data/sample.xlsx")
    df["NewColumn"] = df.iloc[:, 0] * 2
    load_to_csv(df, "output/transformed.csv")
    print("Data saved to output/transformed.csv")
