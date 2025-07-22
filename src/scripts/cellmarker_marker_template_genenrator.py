#!/usr/bin/env python3
"""
cellmarker_marker_template_generator.py


"""
import gzip
import json
import os
from urllib.request import Request, urlopen

import pandas as pd
import requests
from SPARQLWrapper import JSON, SPARQLWrapper

DOWNLOAD_URL = "http://bio-bigdata.hrbmu.edu.cn/CellMarker/CellMarker_download_files/file/Cell_marker_Human.xlsx"
LOCAL_GENE_DATA = "cell_marker_human.xlsx"
OUTPUT_CSV = "cell_marker_human.csv"
SPARQL_ENDPOINT = "https://ubergraph.apps.renci.org/sparql"

script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "../templates/cl_kg/")

_uberon_cache = {}


def download_marker_data(url: str, target: str) -> None:
    """
    Download an Excel file from the given URL and save it to the specified target path.

    Args:
        url (str): The URL to download the Excel file from.
        target (str): The local file path to save the downloaded file.

    Returns:
        None
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(target, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def load_marker_data(path: str) -> pd.DataFrame:
    """
    Load marker data from an Excel or CSV file into a pandas DataFrame.

    Args:
        path (str): Path to the file (.xlsx or .csv).

    Returns:
        pd.DataFrame: DataFrame containing the marker data.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = os.path.splitext(path)[-1].lower()
    if ext == ".xlsx":
        return pd.read_excel(path)
    elif ext == ".csv":
        return pd.read_csv(path)
    else:
        raise ValueError(
            f"Unsupported file format: {ext}. Only .xlsx and .csv are supported."
        )


def query_sparql(label: str, defined_by: str) -> list:
    """
    Generic SPARQL query for terms definedBy `defined_by` with rdfs:label = label^^xsd:string.
    Returns list of URI strings.
    """
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>

    SELECT DISTINCT ?s WHERE {{
      ?s rdfs:isDefinedBy <{defined_by}> ;
         rdfs:label "{label}"^^xsd:string .
    }}"""
    sparql.setQuery(query)
    results = sparql.query().convert()
    return [b["s"]["value"] for b in results["results"]["bindings"]]


def get_uberon_uris(label: str) -> list:
    """Get full UBERON URIs for a tissue label, using a manual cache."""
    if label not in _uberon_cache:
        _uberon_cache[label] = query_sparql(label, "http://purl.obolibrary.org/obo/uberon.owl")
    return _uberon_cache[label]


def process_marker_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process raw marker DataFrame to generate standardized marker annotations.

    Args:
        df (pd.DataFrame): Input DataFrame containing cellontology_id, GeneID, tissue_type, PMID, etc.

    Returns:
        pd.DataFrame: Processed DataFrame with standardized columns.
    """
    result_rows = []

    for row in df.itertuples(index=True):
        if pd.isna(row.cellontology_id) or pd.isna(row.GeneID) or row.cell_type == "Cancer cell":
            continue  # Skip rows with missing GeneID or Cancer cell in cell_type

        cl_id = str(row.cellontology_id).replace("_", ":")
        marker = f"http://identifiers.org/ncbigene/{int(row.GeneID)}"
        marker_symbol = row.Symbol
        tissue = (
            row.uberonongology_id
            if pd.notna(row.uberonongology_id)
            else get_uberon_uris(row.tissue_type)
        )
        tissue = tissue if tissue else ""
        species = "http://purl.obolibrary.org/obo/NCBITaxon_9606"
        source = "http://bio-bigdata.hrbmu.edu.cn/CellMarker/"
        reference = f"PMID:{int(row.PMID)}" if pd.notna(row.PMID) else ""

        result_rows.append(
            {
                "ID": cl_id,
                "MARKER": marker,
                "MARKER_SYMBOL": marker_symbol,
                "TISSUE": tissue,
                "SPECIES": species,
                "SOURCE": source,
                "REFERENCE": reference,
            }
        )

    result_df = pd.DataFrame(result_rows)
    return result_df


def write_csv(df: pd.DataFrame, path: str) -> None:
    """
    Write a pandas DataFrame to a CSV file.

    Args:
        df (pd.DataFrame): The DataFrame to write.
        path (str): The target file path for the CSV output.

    Returns:
        None
    """
    df.to_csv(path, index=False)


def write_templates(marker_df: pd.DataFrame, directory: str) -> None:
    unique_marker_set = set()
    primary_template = os.path.join(
        directory, "cellmarker_marker_annotations_template.tsv"
    )
    with open(primary_template, "w", encoding="utf-8") as out:
        # template header
        out.write("ID\tMARKER\tTISSUE\tSPECIES\tSOURCE\tREFERENCE\n")
        out.write(
            "ID\tAI CLM:0009999\t>AI CLM:0009997\t>AI CLM:0009996\t>AI dcterms:source\t>AI dcterms:references\n"
        )
        for row in marker_df.itertuples(index=True):
            cl_term = row.ID
            gene = row.MARKER
            gene_symbol = row.MARKER_SYMBOL
            unique_marker_set.add((gene, gene_symbol))
            tissue = row.TISSUE
            species = row.SPECIES
            source = row.SOURCE
            reference = row.REFERENCE
            out.write(
                f"{cl_term}\t{gene}\t{tissue}\t{species}\t{source}\t{reference}\n"
            )

    secondary_template = os.path.join(directory, "cellmarker_marker_template.tsv")
    with open(secondary_template, "w", encoding="utf-8") as sout:
        sout.write("ID\tGENE_NAME\tSUPERCLASS\n")
        sout.write("ID\tA rdfs:label\tSC %\n")
        for marker_tuple in unique_marker_set:
            sout.write(f"{marker_tuple[0]}\t{marker_tuple[1]}\tSO:0000704\n")


if __name__ == "__main__":
    if os.path.exists(OUTPUT_CSV):
        print(f"[SKIP] '{OUTPUT_CSV}' already exists.")
        mdf = load_marker_data(OUTPUT_CSV)
    else:
        download_marker_data(DOWNLOAD_URL, LOCAL_GENE_DATA)
        df = load_marker_data(LOCAL_GENE_DATA)
        mdf = process_marker_data(df)
        write_csv(mdf, OUTPUT_CSV)

    write_templates(mdf, output_dir)
