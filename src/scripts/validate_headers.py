import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INPUT_FOLDER_PATH = os.path.join(PROJECT_ROOT, "src/markers/input")

REQUIRED_COLUMNS = ["clusterName", "f_score", "NSForest_markers", "cxg_dataset_title"]

def validate_file(file_path):
    relative_path = os.path.relpath(file_path, PROJECT_ROOT)
    try:
        df = pd.read_csv(file_path, sep=None, engine='python')
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            return f"File {relative_path} is missing columns: {', '.join(missing_columns)}"
        return None
    except Exception as e:
        return f"Error reading {relative_path}: {e}"

def main():
    issues = []

    for file_name in os.listdir(INPUT_FOLDER_PATH):
        if file_name.endswith(".csv") or file_name.endswith(".tsv"):
            file_path = os.path.join(INPUT_FOLDER_PATH, file_name)
            issue = validate_file(file_path)
            if issue:
                issues.append(issue)

    if issues:
        for issue in issues:
            print(issue)
        sys.exit(1)

if __name__ == "__main__":
    main()