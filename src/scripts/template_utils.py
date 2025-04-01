import os

import pandas as pd
from file_utils import read_table_to_dict, read_yaml
from id_manager import IDManager
from neo4j_client import Neo4jClient


TEMPLATES_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../templates/")
MARKERS_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../markers/")

INPUT_FOLDER_PATH = os.path.join(MARKERS_FOLDER_PATH, "input/")
MARKERS_SOURCE_PATH = os.path.join(MARKERS_FOLDER_PATH, "NSForestMarkersSource.tsv")


def process_input_files():
    """
    Process the files in the input folder and generates related Source files.
    """
    neo_client = None
    try:
        neo_client = Neo4jClient("neo4j://172.27.24.69:7687", "", "")

        id_manager = IDManager(MARKERS_FOLDER_PATH)
        gene_db = read_gene_dbs(TEMPLATES_FOLDER_PATH)
        files = os.listdir(INPUT_FOLDER_PATH)
        for file in files:
            full_path = os.path.join(INPUT_FOLDER_PATH, file)
            file_name, file_extension = os.path.splitext(file)
            source_file_path = os.path.join(MARKERS_FOLDER_PATH, f"{file_name}Source.tsv")
            if file_extension in [".csv", ".tsv"] and not os.path.exists(source_file_path):
                print("Processing: " + file)
                input_data = read_table_to_dict(full_path)
                metadata = read_metadata_file(file_name)
                source_data = []
                for row in input_data:
                    if row["clusterName"]:
                        markers_list = row["NSForest_markers"].replace("[", "").replace("]", "").replace("'", "").replace("\"", "").split(",")
                        markers_list = [str(marker).strip() for marker in markers_list]
                        marker_ids_list = [get_gene_id(gene_db, marker) for marker in markers_list]
                        marker_set = id_manager.get_new_id()

                        dataset_name = metadata.get("CxG_dataset", row.get("cxg_dataset_title", ""))
                        cl_info = neo_client.get_cell_info(row["clusterName"], dataset_name)
                        source_data.append({
                            "cl_class": cl_info.get("curie", ""),
                            "cl_label": cl_info.get("label", ""),
                            "Cell_type": row["clusterName"],
                            "Marker_set": marker_set,
                            "Minimal_markers": "|".join(marker_ids_list),
                            "Minimal_markers_label": "|".join(markers_list),
                            "Organ": metadata.get("Organ", ""),
                            "Species": metadata.get("Species", ""),
                            "Species_abbv": metadata.get("Species_abbreviation", ""),
                            "Organ_region": metadata.get("Organ_region", ""),
                            "Parent": "SO:0001260",
                            "FBeta_confidence_score": row["f_score"],
                            "Marker_set_xref": metadata.get("Marker_set_xref", ""),
                            "cxg_dataset_title": dataset_name,
                            "CL_agreed": "False",
                        })

                class_robot_template = pd.DataFrame.from_records(source_data)
                class_robot_template.to_csv(source_file_path, sep="\t", index=False)
                print("Processed: " + file)
                id_manager.skip_ids(1000)
    except Exception as e:
        import traceback
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
    finally:
        if neo_client:
            neo_client.close()


def read_gene_dbs(folder_path: str):
    """
    Reads all TSV files in the templates folder and creates a dictionary of genes
    where the key is the NAME column and the value is the ID column.
    Args:
        folder_path: Path to the folder containing gene TSV files.
    Returns:
        dict: Dictionary with gene NAME as keys and ID as values.

    """
    gene_dict = {}

    for file_name in os.listdir(folder_path):
        if file_name.endswith('.tsv'):
            file_path = os.path.join(folder_path, file_name)
            df = pd.read_csv(file_path, sep='\t')
            for _, row in df.iterrows():
                gene_dict[row['NAME']] = row['ID']

    return gene_dict


def merge_source_files(folder_path, output_path):
    """
    Merges all CSV files in the given folder with the pattern '*Source.csv' into a single CSV file.
    Args:
        folder_path: Path to the folder containing the source CSV files.
        output_path: Path to the output CSV file.
    """
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('Source.tsv')]
    combined_df = pd.concat((pd.read_csv(f, engine='python') for f in all_files), ignore_index=True)
    combined_df.to_csv(output_path, index=False)


def get_gene_id(gene_db, gene_name):
    if str(gene_name) in gene_db:
        return gene_db[str(gene_name)]
    else:
        # gene_db may have styling issues, so workaround
        # TODO remove this workaround after fixing the gene_db
        for gene in gene_db:
            if gene_name.lower() in gene.lower():
                return gene_db[gene]
    raise Exception(f"Gene ID not found for gene: {gene_name}")


def read_metadata_file(input_file_name):
    """
    Reads the metadata file for the given input file from metadata.csv.
    Args:
        input_file_name: name of the input file
    Returns: metadata dictionary
    """
    metadata_file_path = os.path.join(INPUT_FOLDER_PATH, "metadata.csv")

    if os.path.exists(metadata_file_path):
        df = pd.read_csv(metadata_file_path)
        input_file_name = input_file_name.strip()
        file_name_no_ext = os.path.splitext(input_file_name)[0]

        for _, row in df.iterrows():
            row_file_name = row['file_name'].strip()
            row_file_name_no_ext = os.path.splitext(row_file_name)[0]

            if file_name_no_ext == row_file_name_no_ext:
                return row.to_dict()

    raise Exception(f"Metadata not found for file: {input_file_name}")


def extract_gene_terms(output_filepath: str = None, agreed: bool = False):
    """
    Extracts gene terms from the source markers template.
    Args:
        output_filepath: output file path
        agreed: extract only the agreed markers
    Returns: set of gene term ids
    """
    # generate MARKERS_SOURCE_PATH if not exists
    if not os.path.exists(MARKERS_SOURCE_PATH):
        process_input_files()
        merge_source_files(MARKERS_FOLDER_PATH, MARKERS_SOURCE_PATH)
    template = read_table_to_dict(MARKERS_SOURCE_PATH)
    gene_terms = set()
    for row in template:
        if agreed and str(row.get("CL_agreed", "false")).strip().lower() != "true":
            continue
        gene_terms.update(row["Minimal_markers"].split("|"))
    gene_terms = {str(gene).strip() for gene in gene_terms}
    if output_filepath:
        with open(output_filepath, "w") as f:
            for term in gene_terms:
                f.write(term + "\n")
    return gene_terms