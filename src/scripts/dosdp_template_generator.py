import os
import argparse
import ssl

import urllib.request
import pandas as pd
from rdflib import Graph
from file_utils import read_table_to_dict
from robot_template_generator import generate_kg_indvs_robot_template

from template_utils import MARKERS_FOLDER_PATH, MARKERS_SOURCE_PATH, process_input_files, merge_source_files, extract_gene_terms


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

