import os
import requests
import pandas as pd
from neo4j import GraphDatabase
from io import StringIO

# Directory for saving the output files
output_dir = "src/templates/cl_kg"

# Neo4j connection details
neo4j_uri = "bolt://172.27.24.69:7687"

# Cypher query to get GO terms
query = """
MATCH (c:Cell)-[]-(g)
WHERE g.curie STARTS WITH 'GO:'
RETURN g.curie
"""

# QuickGO base URL
quickgo_base_url = "https://www.ebi.ac.uk/QuickGO/services/annotation/downloadSearch"

# Valid selectedFields for QuickGO API
selected_fields = [
    "goId",  # The GO ID
    "geneProductId",  # The gene product ID
    "goEvidence",  # The evidence supporting the annotation
    "reference",  # References associated with the annotation
    "taxonId",  # The taxonomic identifier
    "qualifier",  # The qualifier of the GO annotation
    "symbol",  # The gene symbol
    "name",  # Additional name field
]

include_fields = ["goName", "taxonName"]

# Parameters template for QuickGO API
quickgo_params_template = [
    ("goUsageRelationships", "is_a,part_of,occurs_in"),
    ("taxonId", "9606,10090"),
    ("taxonUsage", "descendants"),
    ("evidenceCode", "ECO:0000269"),
    ("evidenceCodeUsage", "descendants"),
]

# Relation to Curie mapping with underscores in keys
relation_to_curie = {
    "acts_upstream_of_or_within": "RO:0002264",
    "involved_in": "RO:0002331",
    "acts_upstream_of": "RO:0002263",
    "located_in": "RO:0001025",
    "acts_upstream_of_or_within_positive_effect": "RO:0004032",
    "is_active_in": "RO:0002432",
    "colocalizes_with": "RO:0002325",
    "part_of": "BFO:0000050",
    "enables": "RO:0002327",
    "acts_upstream_of_or_within_negative_effect": "RO:0004033",
    "acts_upstream_of_positive_effect": "RO:0004034",
    "acts_upstream_of_negative_effect": "RO:0004035",
    "contributes_to": "RO:0002326",
}


def get_curies():
    driver = GraphDatabase.driver(neo4j_uri)
    curies = set()
    try:
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                curies.add(record["g.curie"])
    finally:
        driver.close()
    return curies


def fetch_data_for_go_curie(go_curie):
    params = quickgo_params_template.copy()
    params.append(("goId", go_curie))

    for field in include_fields:
        params.append(("includeFields", field))

    for field in selected_fields:
        params.append(("selectedFields", field))

    response = requests.get(
        quickgo_base_url, params=params, headers={"Accept": "text/tsv"}, timeout=60
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch data for {go_curie}: {response.status_code} - {response.text}"
        )

    tsv_data = StringIO(response.text)
    df = pd.read_csv(tsv_data, sep="\t")

    return df


def process_qualifier_subset(df, qualifier, curie_mapping, base_first_row):
    subset_df = df[df["QUALIFIER"] == qualifier].copy()
    new_first_row = base_first_row.copy()
    new_first_row["GENE PRODUCT ID"] = "AI " + curie_mapping.get(qualifier, "")
    new_first_row.drop(columns=["QUALIFIER"], inplace=True)
    subset_df.drop(columns=["QUALIFIER"], inplace=True)
    return pd.concat([new_first_row, subset_df], ignore_index=True)


def main():
    # Fetch data from Neo4j and QuickGO API
    go_curies = get_curies()
    combined_df = pd.DataFrame()

    for go_curie in go_curies:
        try:
            go_df = fetch_data_for_go_curie(go_curie)
            combined_df = pd.concat([combined_df, go_df], ignore_index=True)
        except Exception as e:
            print(f"Error fetching data for {go_curie}: {e}")

    # Filter for UniProtKB entries and remove unwanted qualifiers
    combined_df.drop_duplicates(inplace=True)
    filtered_uniprot_df = combined_df[
        combined_df["GENE PRODUCT DB"] == "UniProtKB"
    ].loc[~combined_df["QUALIFIER"].str.contains("NOT\|", na=False)]

    # ETL transformation
    filtered_uniprot_df["GENE PRODUCT ID"] = (
        "https://identifiers.org/uniprot:" + filtered_uniprot_df["GENE PRODUCT ID"]
    )
    filtered_uniprot_df["TAXON ID"] = (
        "http://purl.obolibrary.org/obo/NCBITaxon_"
        + filtered_uniprot_df["TAXON ID"].astype(str)
    )
    filtered_uniprot_df.rename(columns={"GO TERM": "ID"}, inplace=True)

    # Prepare quick_go_template
    quick_go_template = filtered_uniprot_df[
        [
            "ID",
            "GENE PRODUCT ID",
            "GO EVIDENCE CODE",
            "REFERENCE",
            "TAXON ID",
            "QUALIFIER",
        ]
    ].copy()

    first_row_values_template = {
        "ID": "ID",
        "GENE PRODUCT ID": "AI RO:0002264",
        "GO EVIDENCE CODE": ">A oboInOwl:evidence",
        "REFERENCE": ">A oboInOwl:hasDbXref",
        "TAXON ID": "AI RO:0002162",
        "QUALIFIER": "",
    }
    first_row_df_template = pd.DataFrame([first_row_values_template])
    quick_go_template = pd.concat(
        [first_row_df_template, quick_go_template], ignore_index=True
    )

    # Prepare quick_go_protein_template
    quick_go_protein_template = filtered_uniprot_df[
        ["GENE PRODUCT ID", "SYMBOL", "GENE_PRODUCT_NAME"]
    ].copy()
    quick_go_protein_template.rename(columns={"GENE PRODUCT ID": "ID"}, inplace=True)

    first_row_values_protein = {
        "ID": "ID",
        "SYMBOL": "A IAO:0000028",
        "GENE_PRODUCT_NAME": "A rdfs:label",
    }
    first_row_df_protein = pd.DataFrame([first_row_values_protein])
    quick_go_protein_template = pd.concat(
        [first_row_df_protein, quick_go_protein_template], ignore_index=True
    )

    # Split the quick_go_template by QUALIFIER
    base_first_row = quick_go_template.iloc[[0]].copy()
    dataframes_by_qualifier = {}

    for qualifier in quick_go_template["QUALIFIER"].unique():
        if pd.notna(qualifier) and qualifier != "":
            df_subset = process_qualifier_subset(
                quick_go_template.iloc[1:], qualifier, relation_to_curie, base_first_row
            )
            dataframes_by_qualifier[qualifier] = df_subset

    # Save files to the output directory
    for qualifier, df in dataframes_by_qualifier.items():
        file_name = os.path.join(
            output_dir,
            qualifier.replace(" ", "_").replace(":", "").lower()
            + "_quick_go_template.tsv",
        )
        df.to_csv(file_name, sep="\t", index=False)

    quick_go_protein_template.to_csv(
        os.path.join(output_dir, "quick_go_protein_template.tsv"), sep="\t", index=False
    )


if __name__ == "__main__":
    main()