import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INPUT_FOLDER_PATH = os.path.join(PROJECT_ROOT, "src/markers/input")

REQUIRED_COLUMNS = ["clusterName", "f_score", "NSForest_markers"]
METADATA_FILE_PATH = os.path.join(INPUT_FOLDER_PATH, "metadata.csv")
METADATA_REQUIRED_COLUMNS = ["file_name", "Organ", "Species", "Species_abbreviation", "Organ_region", "Parent", "Marker_set_xref"]


def validate_file_headers(file_path):
    relative_path = os.path.relpath(file_path, PROJECT_ROOT)
    try:
        df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8-sig')
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns.tolist()]
        if missing_columns:
            return f"File {relative_path} is missing columns: {', '.join(missing_columns)}"
        return None
    except pd.errors.ParserError as e:
        return f"Parsing error in {relative_path}: {e}"
    except Exception as e:
        return f"Error reading {relative_path}: {e}"

def validate_input_headers(issues):
    for file_name in os.listdir(INPUT_FOLDER_PATH):
        if (file_name.endswith(".csv") or file_name.endswith(".tsv")) and not file_name.startswith(
                "metadata.csv"):
            file_path = os.path.join(INPUT_FOLDER_PATH, file_name)
            issue = validate_file_headers(file_path)
            if issue:
                issues.append(issue)

def validate_metadata_record(file_name, metadata_df):
    file_name_no_ext = os.path.splitext(file_name)[0]
    metadata_record = metadata_df[metadata_df['file_name'].str.strip().str.split('.').str[0] == file_name_no_ext]

    if metadata_record.empty:
        return f"Metadata record not found for file: {file_name}. Please update the src/markers/input/metadata.csv file."

    for col in METADATA_REQUIRED_COLUMNS:
        if pd.isna(metadata_record.iloc[0][col]) or metadata_record.iloc[0][col] == "":
            return f"Metadata record in metadata.csv for {file_name} is missing value in column: {col}"
    return None

def validate_metadata(issues):
    metadata_df = pd.read_csv(METADATA_FILE_PATH)
    for file_name in os.listdir(INPUT_FOLDER_PATH):
        if (file_name.endswith(".csv") or file_name.endswith(".tsv")) and not file_name.startswith("metadata.csv"):
            issue = validate_metadata_record(file_name, metadata_df)
            if issue:
                issues.append(issue)

def main():
    issues = []

    validate_input_headers(issues)
    validate_metadata(issues)

    if issues:
        for issue in issues:
            print(issue)
        sys.exit(1)


if __name__ == "__main__":
    main()