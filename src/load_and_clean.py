import os
import pandas as pd

DATA_DIR = os.path.expanduser("~/Documents/Finance/FinanceAnalyzer/data")

def load_and_clean_csv(filename: str) -> pd.DataFrame:
    """
    Loads and cleans a CSV file from the data directory.
    Skips metadata and starts processing from the header row.
    Returns a cleaned pandas DataFrame.
    """
    file_path = os.path.join(DATA_DIR, filename)
    header_keywords = [
        "Txn Date", "Value Date", "Cheque No.", "Description",
        "Branch Code", "Debit", "Credit", "Balance"
    ]

    # Find the header row number
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if all(keyword in line for keyword in header_keywords):
                header_row = i
                break
        else:
            raise ValueError("Header row with expected columns not found.")

    # Read the CSV starting from the header row
    df = pd.read_csv(
        file_path,
        header=19,
        dtype=str,
        engine="python"
    )

    # Remove rows where all columns are NaN
    df.dropna(how='all', inplace=True)

    # Clean up column names to remove leading/trailing spaces
    df.columns = [col.strip() for col in df.columns]

    # Remove leading =' and trailing " if present
    for col in ["Txn Date", "Value Date", "Cheque No.", "Description", "Branch Code", "Debit", "Credit", "Balance"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'^="|"$', '', regex=True).str.strip()

    # Convert Debit, Credit, Balance to float (handle commas and 'None')
    for col in ["Debit", "Credit", "Balance"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .replace(['', 'None', None], '0')
                .str.replace(',', '', regex=False)
                .astype(float)
            )

    print(f"Loaded {len(df)} rows from {filename}")

    return df

def load_all_data():
    """
    Loads and cleans all CSV files in the data directory.
    Returns a list of DataFrames.
    """
    dataframes = []
    for fname in os.listdir(DATA_DIR):
        if fname.lower().endswith('.csv'):
            df = load_and_clean_csv(fname)
            dataframes.append(df)
    return dataframes

# Example usage:
if __name__ == "__main__":
    dfs = load_all_data()
    print(f"Loaded {len(dfs)} files.")