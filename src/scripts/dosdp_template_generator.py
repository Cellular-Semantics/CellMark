import os
import argparse

import pandas as pd
from rdflib import Graph
from file_utils import read_table_to_dict


MARKERS_SOURCE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../markers/NSForestMarkersSource.tsv")
CL_URL = "https://raw.githubusercontent.com/obophenotype/cell-ontology/master/cl-base.owl"


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
        class_template.append({
            "defined_class": row["Marker_set"],
            "Marker_set_of": get_cl_label(cl_ontology, row["class"]),
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
            "defined_class": row["class"],
            "Cell_type": row["class"],
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
    g = Graph()
    g.parse(ontology_path, format="xml")
    return g


def get_cl_label(graph, cl_id):
    """
    Query the ontology graph to get the label of the CL term.
    """
    response = graph.query(f"""
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix CL: <http://purl.obolibrary.org/obo/CL_>
        SELECT ?label
        WHERE {{
            {cl_id} rdfs:label ?label .
        }}
    """)
    return response.bindings[0]["label"]


def extract_gene_terms(output_filepath: str = None):
    """
    Extracts gene terms from the source markers template.
    Args:
        output_filepath: output file path
    Returns: set of gene term ids
    """
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
        exit(1)

