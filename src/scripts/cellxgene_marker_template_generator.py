#!/usr/bin/env python3
"""
cellxgene_marker_template_generator.py

Downloads and parses marker-gene JSON data from CxG (cellxgene),
then provides functions to look up UBERON and NCBITaxon URIs via SPARQL,
NCBIgene URIs via MyGene.info (with caching),
and generates both a remapped JSON (new_marker.json) and a ROBOT template TSV
(cellxgene_marker_template.tsv) for OWL generation.
"""
import os
import gzip
import json
from urllib.request import urlopen, Request
from SPARQLWrapper import SPARQLWrapper, JSON
import requests

# Constants
THRESHOLD = 1.0  # only include markers with score >= this value
DOWNLOAD_URL = (
    "https://cellguide.cellxgene.cziscience.com/"
    "1717264981/computational_marker_genes/marker_gene_data.json.gz"
)
LOCAL_JSON = "marker_gene_data.json"
OUTPUT_JSON = "new_marker.json"
SPARQL_ENDPOINT = "https://ubergraph.apps.renci.org/sparql"
MYGENE_ENDPOINT = "http://mygene.info/v3/query"

# Simple cache for gene lookups to avoid redundant HTTP calls
gene_cache = {}

script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "../templates/cl_kg/")


def download_marker_data(url: str, target: str) -> None:
    """
    Download and decompress a .json.gz to `target`, skipping if it exists.
    """
    if os.path.exists(target):
        print(f"[SKIP] '{target}' already exists.")
        return
    print(f"Downloading and decompressing {url}...")
    req = Request(url, headers={"User-Agent": "python-urllib"})
    with urlopen(req) as resp, gzip.open(resp, 'rt') as gz, open(target, 'w', encoding='utf-8') as out:
        out.write(gz.read())
    print(f"Saved to {target}.")


def load_marker_data(path: str) -> dict:
    """Load the marker JSON into a Python dict."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    return [b['s']['value'] for b in results['results']['bindings']]


def get_uberon_uris(label: str) -> list:
    """Get full UBERON URIs for a tissue label."""
    return query_sparql(label, "http://purl.obolibrary.org/obo/uberon.owl")


def get_ncbitaxon_uris(label: str) -> list:
    """Get full NCBITaxon URIs for an organism label."""
    return query_sparql(label, "http://purl.obolibrary.org/obo/ncbitaxon.owl")


def get_ncbigene_uri(gene_label: str, taxid: str) -> str:
    """
    Query MyGene.info for the gene_label and taxid, return the identifiers.org NCBIgene URI.
    Uses 'entrezonly' parameter to ensure only numeric hits are returned,
    and caches results to avoid redundant HTTP calls.
    """
    key = (gene_label, taxid)
    if key in gene_cache:
        return gene_cache[key]
    if "_ENSMUSG" in gene_label or "ENSG" in gene_label:
        gene_label = gene_label.split("_ENS")[0]
    params = {"q": gene_label, "species": taxid, "entrezonly": True}
    resp = requests.get(MYGENE_ENDPOINT, params=params, timeout=5)
    try:
        data = resp.json()
    except json.decoder.JSONDecodeError:
        print(resp.json())
    hits = data.get('hits', [])
    uri = None
    if hits:
        # Only need to consider the first hit, since 'entrezonly' ensures numeric IDs
        first = hits[0]
        candidate = first.get('_id') or first.get('entrezgene')
        if candidate:
            uri = f"http://identifiers.org/ncbigene/{candidate}"
    else:
        print(f"Warning: no NCBIgene hit for '{gene_label}' (taxid={taxid})")

    gene_cache[key] = uri
    return uri


def build_mapping(data: dict) -> dict:
    """
    Build mapping from organism taxon URI -> tissue UBERON URI -> CL term -> filtered markers.
    Only includes markers with score >= THRESHOLD and replaces gene labels with NCBIgene URIs.
    """
    mapped = {}
    for species_label, tissues in data.items():
        taxon_uris = get_ncbitaxon_uris(species_label)
        for tax_uri in taxon_uris:
            taxid = tax_uri.split('_')[-1]
            mapped.setdefault(tax_uri, {})
            for tissue_label, cl_groups in tissues.items():
                if tissue_label == "All Tissues":
                    continue
                uberon_uris = get_uberon_uris(tissue_label)
                for uberon_uri in uberon_uris:
                    mapped[tax_uri].setdefault(uberon_uri, {})
                    for cl_term, markers in cl_groups.items():
                        # filter by threshold
                        filtered = [m for m in markers if m.get('marker_score', 0) >= THRESHOLD][
                                   :10]
                        # convert genes to URIs using cache
                        for m in filtered:
                            gene_uri = get_ncbigene_uri(m.get('gene', ''), taxid)
                            if gene_uri:
                                m['gene'] = gene_uri
                        mapped[tax_uri][uberon_uri][cl_term] = filtered
    return mapped


def write_json(mapping: dict, output: str) -> None:
    """Write the mapping dict to a JSON file."""
    with open(output, 'w', encoding='utf-8') as out:
        json.dump(mapping, out, indent=2)
    print(f"Remapped JSON written to {output}")


def write_template(mapping: dict, output: str) -> None:
    """
    Write a ROBOT template TSV based on mapping.

    Two header rows:
    ID	MARKER	MARKER_SCORE	CELL_RATIO	TISSUE  SPECIES
    ID	A hm:has_marker	>A hm:marker_score	>A hm:cell_ratio	>AI hm:context  >AI hm:species
    """
    with open(output, 'w', encoding='utf-8') as out:
        # template header
        out.write("ID\tMARKER\tMARKER_SCORE\tCELL_RATIO\tTISSUE\tSPECIES\n")
        out.write("ID\tA hm:has_marker\t>A hm:marker_score\t>A hm:cell_ratio\t>AI hm:context\t>AI hm:species\n")
        for taxon_uri, tissues in mapping.items():
            for uberon_uri, cl_map in tissues.items():
                for cl_term, markers in cl_map.items():
                    for m in markers:
                        gene = m.get('gene', '')
                        if "ncbigene" not in gene:
                            continue
                        score = m.get('marker_score', '')
                        ratio = m.get('pc', '')
                        # write row
                        out.write(f"{cl_term}\t{gene}\t{score}\t{ratio}\t{uberon_uri}\t{taxon_uri}\n")


if __name__ == '__main__':
    if os.path.exists(OUTPUT_JSON):
        print(f"[SKIP] '{OUTPUT_JSON}' already exists.")
        mapping = load_marker_data(OUTPUT_JSON)
        # summary counts
        total = sum(
            len(markers)
            for tissues in mapping.values()
            for cl_groups in tissues.values()
            if isinstance(cl_groups, dict)
            for markers in cl_groups.values()
        )
        print(f"Total gene objects overall: {total}")
    else:
        download_marker_data(DOWNLOAD_URL, LOCAL_JSON)
        data = load_marker_data(LOCAL_JSON)
        mapping = build_mapping(data)
        write_json(mapping, OUTPUT_JSON)

        # summary counts
        total = sum(
            len(markers)
            for tissues in data.values()
            for cl_groups in tissues.values()
            if isinstance(cl_groups, dict)
            for markers in cl_groups.values()
        )
        above = sum(
            1
            for tissues in data.values()
            for cl_groups in tissues.values()
            if isinstance(cl_groups, dict)
            for markers in cl_groups.values()
            for m in markers
            if m.get('marker_score', 0) >= THRESHOLD
        )
        print(f"Total gene objects overall: {total}")
        print(f"Total gene objects with marker_score >= {THRESHOLD}: {above}")

    # generate ROBOT template TSV
    tsv_file = os.path.join(output_dir, "cellxgene_marker_template.tsv")
    write_template(mapping, tsv_file)
    print(f"ROBOT template TSV written to {tsv_file}")
