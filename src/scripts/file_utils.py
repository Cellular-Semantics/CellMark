import os


def read_table_to_dict(path: str):
    """
    Reads a table from a file and returns as a list of dictionaries per row.
    Args: path: path to the table file
    Returns: list of dictionaries
    """
    _, file_extension = os.path.splitext(path)
    separator = "," if file_extension == ".csv" else "\t"

    with open(path) as f:
        lines = f.readlines()
    header = lines[0].strip().split(separator)
    data = []
    for line in lines[1:]:
        row = line.strip().split(separator)
        data.append(dict(zip(header, row)))
    return data


