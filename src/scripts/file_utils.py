import os
import csv
import yaml


def read_table_to_dict(path: str):
    """
    Reads a table from a file and returns as a list of dictionaries per row.
    Args: path: path to the table file
    Returns: list of dictionaries
    """
    _, file_extension = os.path.splitext(path)
    delimiter = "," if file_extension == ".csv" else "\t"

    with open(path, encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader)
        data = [dict(zip(header, row)) for row in reader]
    return data


def read_yaml(file_path: str) -> dict:
    """
    Reads a YAML file and creates a dictionary from its values.
    Args:
        file_path: Path to the YAML file.
    Returns:
        dict: Dictionary with YAML file contents.
    """
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    return data

