import os
import argparse
import ssl

import urllib.request
import pandas as pd
from rdflib import Graph
from file_utils import read_table_to_dict, read_yaml
from neo4j_client import Neo4jClient
from id_manager import IDManager


MARKERS_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../markers/")
INPUT_FOLDER_PATH = os.path.join(MARKERS_FOLDER_PATH, "input/")

TEMPLATES_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../templates/")
MARKERS_SOURCE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../markers/NSForestMarkersSource.tsv")
CL_KG_TEMPLATE_PATH = os.path.join(TEMPLATES_FOLDER_PATH, "cl_kg/Clusters.tsv")
CL_URL = "https://raw.githubusercontent.com/obophenotype/cell-ontology/master/cl-base.owl"

# Create an unverified SSL context
ssl_context = ssl._create_unverified_context()


def generate_nsforest_markers_template(agreed: bool, output_filepath: str):
    """
    Generates a template for NSForestMarkers pattern.
    Args:
        agreed: generate only the agreed markers
        output_filepath: output file path
    """
    cl_ontology = _init_graph(CL_URL)
    source = read_table_to_dict(MARKERS_SOURCE_PATH)
    class_template = []
    for row in source:
        if agreed and str(row.get("CL_agreed", "false")).strip().lower() != "true":
            continue
        if agreed and str(row.get("CL_agreed", "false")).strip().lower() == "true" and not str(row["cl_class"]).startswith("CL:"):
            raise ValueError(f"Agreed marker '{row['cl_class']}' is not a CL term.")
        class_template.append({
            "defined_class": row["Marker_set"],
            "Marker_set_of": get_cl_label(cl_ontology, row["cl_class"], row["Cell_type"]),
            "Minimal_markers": row["Minimal_markers"],
            "Minimal_markers_label": row["Minimal_markers_label"],
            "Organ": row["Organ"],
            "Species_abbv": row["Species_abbv"],
            "Organ_region": row["Organ_region"],
            "Parent": row["Parent"],
            "FBeta_confidence_score": row["FBeta_confidence_score"],
        })

    class_robot_template = pd.DataFrame.from_records(class_template)
    class_robot_template.to_csv(output_filepath, sep="\t", index=False)


def generate_markers_to_cells_template(agreed: bool, output_filepath: str):
    """
    Generates a template for MarkersToCells pattern.
    Args:
        agreed: generate only the agreed markers
        output_filepath: output file path
    """
    # cl_ontology = _init_graph(CL_URL)
    source = read_table_to_dict(MARKERS_SOURCE_PATH)
    class_template = []
    for row in source:
        if agreed and str(row.get("CL_agreed", "false")).strip().lower() != "true":
            continue
        class_template.append({
            "defined_class": row["cl_class"],
            "Cell_type": row["cl_class"],
            "has_characterization_set": row["Marker_set"],
            "Marker_set": row["Minimal_markers_label"],
            "Organ": row["Organ"],
            "Species_abbv": row["Species_abbv"],
            "Species": row["Species"],
            "FBeta_confidence_score": row.get("FBeta_confidence_score", ""),
            "Marker_set_xref": row.get("Marker_set_xref", "")
        })

    class_robot_template = pd.DataFrame.from_records(class_template)
    class_robot_template.to_csv(output_filepath, sep="\t", index=False)


def _init_graph(ontology_path):
    """
    Load the given ontology into a Graph object.

    Args:
        ontology_path (str): The url or filepath of the ontology.

    Returns:
        rdflib.Graph: The loaded ontology graph.
    """
    temp_file = "cl-base.owl"
    response = urllib.request.urlopen(ontology_path, context=ssl_context)
    data = response.read()
    with open(temp_file, 'wb') as file:
        file.write(data)

    g = Graph()
    g.parse(temp_file, format="xml")

    delete_file(temp_file)
    return g


def get_cl_label(graph, cl_id, alt_label):
    """
    Query the ontology graph to get the label of the CL term.
    """
    if cl_id.startswith("CL:"):
        response = graph.query(f"""
            prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            prefix CL: <http://purl.obolibrary.org/obo/CL_>
            SELECT ?label
            WHERE {{
                {cl_id} rdfs:label ?label .
            }}
        """)
        return response.bindings[0]["label"]
    else:
        return alt_label


def extract_gene_terms(output_filepath: str = None):
    """
    Extracts gene terms from the source markers template.
    Args:
        output_filepath: output file path
    Returns: set of gene term ids
    """
    # generate MARKERS_SOURCE_PATH if not exists
    if not os.path.exists(MARKERS_SOURCE_PATH):
        process_input_files()
        merge_source_files(MARKERS_FOLDER_PATH, MARKERS_SOURCE_PATH)
    template = read_table_to_dict(MARKERS_SOURCE_PATH)
    gene_terms = set()
    for row in template:
        gene_terms.update(row["Minimal_markers"].split("|"))
    gene_terms = {str(gene).strip() for gene in gene_terms}
    if output_filepath:
        with open(output_filepath, "w") as f:
            for term in gene_terms:
                f.write(term + "\n")
    return gene_terms


def process_input_files():
    """
    Process the files in the input folder and generates related Source files.
    """
    id_manager = IDManager(MARKERS_FOLDER_PATH)
    gene_db = read_gene_dbs(TEMPLATES_FOLDER_PATH)
    files = os.listdir(INPUT_FOLDER_PATH)
    for file in files:
        full_path = os.path.join(INPUT_FOLDER_PATH, file)
        file_name, file_extension = os.path.splitext(file)
        source_file_path = os.path.join(MARKERS_FOLDER_PATH, f"{file_name}Source{file_extension}")
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
                    source_data.append({
                        "cl_class": "",
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
                        "cxg_dataset_title": metadata.get("CxG_dataset", row.get("cxg_dataset_title", "")),
                        "CL_agreed": "False",
                    })

            class_robot_template = pd.DataFrame.from_records(source_data)
            class_robot_template.to_csv(source_file_path, sep="\t", index=False)
            print("Processed: " + file)
            id_manager.skip_ids(1000)


def generate_kg_indvs_robot_template():
    """
    Generates the CL_KG Cluster individuals robot template. Dosdp doesn't support ontology
    individuals creation. This template is counterpart of the `MarkersToCells.tsv` dosdp template.

    CK_KG Cluster individuals has auto-generated IDs. So this template should be regenerated with
    each CL_KG update.
    """
    neo_client = None
    try:
        neo_client = Neo4jClient("neo4j://172.27.24.69:7687", "", "")
        source_table = read_table_to_dict(MARKERS_SOURCE_PATH)

        robot_template_seed = {'ID': 'ID',
                               'TYPE': 'TYPE',
                               'Cell_type': 'A skos:prefLabel',
                               'Marker_set': "I RO:0015004",
                               'Comment': 'A rdfs:comment',
                               'Species': 'AI RO:0002175 SPLIT=|',
                               }
        dl = [robot_template_seed]

        for row in source_table:
            if row.get("cxg_dataset_title"):
                cluster_ids = get_cluster_ids(neo_client, row["Cell_type"].strip(), row.get("cxg_dataset_title"))
                for cluster_id in cluster_ids:
                    dl.append({
                        "ID": cluster_id,
                        "TYPE": "owl:NamedIndividual",
                        "Cell_type": row["Cell_type"],
                        "Marker_set": row["Marker_set"],
                        "Comment": "A {} in the {} {} has the gene markers {} with a NS-Forest FBeta value of {}s.".format(row["Cell_type"], row["Species_abbv"], row["Organ"], ', '.join(row["Minimal_markers_label"].split("|")), row["FBeta_confidence_score"]),
                        "Species": row["Species"],
                    })

        class_robot_template = pd.DataFrame.from_records(dl)
        class_robot_template.to_csv(CL_KG_TEMPLATE_PATH, sep="\t", index=False)
        print("CL clusters Robot template generated: " + CL_KG_TEMPLATE_PATH)
    except Exception as e:
        import traceback
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
    finally:
        if neo_client:
            neo_client.close()


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


def get_cluster_ids(neo_client, cluster_name, cxg_dataset):
    """
    Get the cluster ID from the neo4j.
    :param neo_client: neo4j client
    :param cluster_name: name of the cluster
    :param cxg_dataset: name of the CellxGene dataset
    :return: iris of the cluster. Returns a list with an empty string if cannot find the cluster.
    """
    cluster_iris = [""]
    if cxg_dataset:
        cluster_iris = neo_client.get_cell_cluster_iri(cluster_name, cxg_dataset)
        if not cluster_iris:
            print(f"!!! Cluster '{cluster_name}' not found in the database.")
            cluster_iris = [""]

    return cluster_iris


def read_metadata_file(input_file_name):
    """
    Reads the metadata file for the given input file.
    Args:
        input_file_name: name of the input file
    Returns: metadata dictionary
    """
    metadata_file_path = os.path.join(INPUT_FOLDER_PATH, f"{input_file_name}.yaml")
    metadata = {}
    if os.path.exists(metadata_file_path):
        metadata = read_yaml(metadata_file_path)
    return metadata


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
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('Source.csv')]
    combined_df = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)
    combined_df.to_csv(output_path, index=False)


def delete_file(path):
    if os.path.exists(path):
        os.remove(path)


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    subparsers = cli.add_subparsers(help="Available actions", dest="action")

    parser_generate = subparsers.add_parser("generate", description="Template generator")
    parser_generate.add_argument("-t", "--template", type=str, help="Name of the template to generate")
    parser_generate.add_argument("-a", "--agreed", action="store_true", help="Generate only the CL agreed markers")
    parser_generate.add_argument("-o", "--out", type=str, help="Output file path")
    parser_generate.set_defaults(agreed=False)

    parser_terms = subparsers.add_parser("terms", description="Template terms extractor")
    parser_terms.add_argument("-o", "--out", type=str, help="Output file path")

    args = cli.parse_args()

    delete_file(MARKERS_SOURCE_PATH)
    process_input_files()
    merge_source_files(MARKERS_FOLDER_PATH, MARKERS_SOURCE_PATH)
    generate_kg_indvs_robot_template()

    if args.action == "generate":
        if args.template == "NSForestMarkers":
            generate_nsforest_markers_template(args.agreed, args.out)
        elif args.template == "MarkersToCells":
            generate_markers_to_cells_template(args.agreed, args.out)
        else:
            print("Invalid template name: {}".format(args.template))
            exit(1)
    elif args.action == "terms":
        extract_gene_terms(args.out)
    else:
        print("Invalid action: {}".format(args.action))
        delete_file(MARKERS_SOURCE_PATH)
        exit(1)

    # clean temp products
    delete_file(MARKERS_SOURCE_PATH)

