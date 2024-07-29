
def read_table_to_dict(path: str):
    """
    Reads a table from a file and returns as a list of dictionaries per row.
    Args: path: path to the table file
    Returns: list of dictionaries
    """
    with open(path) as f:
        lines = f.readlines()
    header = lines[0].strip().split("\t")
    data = []
    for line in lines[1:]:
        row = line.strip().split("\t")
        data.append(dict(zip(header, row)))
    return data
