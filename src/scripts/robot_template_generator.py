import os
import ssl
import argparse
import pandas as pd

from neo4j_client import Neo4jClient
from SPARQLWrapper import SPARQLWrapper, JSON
from cachetools import TTLCache, cached

from file_utils import read_table_to_dict
from template_utils import TEMPLATES_FOLDER_PATH, MARKERS_SOURCE_PATH, extract_gene_terms

SHARED_DRIVE = "/Volumes/osumi-sutherland/development"

CL_KG_TEMPLATE_PATH = os.path.join(TEMPLATES_FOLDER_PATH, "cl_kg/Clusters.tsv")


def extract_genes_from_anndata(anndata_path, gene_name_column, prefix, output_path, use_backed=False):
    """
    Extracts gene names from the AnnData object and saves them to a ROBOT template.
    Params:
        anndata_path: path to the AnnData object.
        gene_name_column: column name containing the gene names.
        prefix: prefix for the gene IDs (such as ensembl or ncbigene).
        output_path: path to the output file.
        use_backed: load AnnData in backed mode (memory efficient, slower).
    """
    import anndata as ad  # Importing anndata here to avoid unnecessary dependency in the main script that cause ODK failure

    if os.path.exists(anndata_path):
        anndata = ad.read_h5ad(anndata_path, backed='r' if use_backed else False)
    elif os.path.exists(SHARED_DRIVE):
        shared_path = os.path.join(SHARED_DRIVE, anndata_path)
        anndata = ad.read_h5ad(shared_path, backed='r' if use_backed else False)
    else:
        raise FileNotFoundError(f"File not found: {anndata_path}. Consider mounting the shared drive.")
    genes = anndata.var.index.unique().tolist()
    records = list()
    records.append(['ID', 'SC %', 'A rdfs:label', 'A oboInOwl:hasExactSynonym SPLIT=|'])
    for gene_id in genes:
        data = [prefix + ':' + gene_id, 'SO:0000704', anndata.var.loc[gene_id][gene_name_column], '']
        records.append(data)

    df = pd.DataFrame(records, columns=["ID", "TYPE", "NAME", "SYNONYMS"])
    df.to_csv(output_path, sep="\t", index=False)
    if use_backed and hasattr(anndata, "file") and anndata.file is not None:
        anndata.file.close()


def generate_genes_robot_template(input_files: list, output_filepath: str, agreed: bool = False):
    robot_template_seed = {'ID': 'ID',
                           'TYPE': 'SC %',
                           'NAME': 'A rdfs:label',
                           'SYNONYMS': 'A oboInOwl:hasExactSynonym SPLIT=|'
                           }
    dl = [robot_template_seed]

    used_genes = extract_gene_terms(agreed=agreed)
    found_genes = []
    for input_file in input_files:
        records = read_table_to_dict(input_file)
        for record in records:
            if record['ID'] in used_genes and record['ID'] not in found_genes:
                dl.append(record)
                found_genes.append(record['ID'])
    missing_genes = used_genes - set(found_genes)
    if missing_genes:
        print(f"Missing genes: {missing_genes}")
        raise ValueError(f"Following genes couldn't be found in the reference DBs: {missing_genes}")
    df = pd.DataFrame(dl)
    df.to_csv(output_filepath, sep="\t", index=False)


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
                               'Marker_set': "AI CLM:0010000",
                               'Comment': 'A rdfs:comment',
                               'Species': 'AI RO:0002175 SPLIT=|',
                               }
        dl = [robot_template_seed]

        for row in source_table:
            if row.get("cxg_dataset_title"):
                cluster_ids = get_cluster_ids(neo_client, row["Cell_type"].strip(), row.get("cxg_dataset_title"))
                for cluster_id in cluster_ids:
                    if cluster_id:
                        dl.append({
                            "ID": cluster_id,
                            "TYPE": "owl:NamedIndividual",
                            "Cell_type": row["Cell_type"],
                            "Marker_set": row["Marker_set"],
                            "Comment": "A {} in the {} {} has the gene markers {} with a NS-Forest FBeta value of {}s.".format(row["Cell_type"], row["Species_abbv"], get_uberon_label(row["Organ_region"]), ', '.join(row["Minimal_markers_label"].split("|")), row["FBeta_confidence_score"]),
                            "Species": row["Species"],
                        })

        class_robot_template = pd.DataFrame.from_records(dl)
        class_robot_template.to_csv(CL_KG_TEMPLATE_PATH, sep="\t", index=False)
        print("CL clusters Robot template generated: " + CL_KG_TEMPLATE_PATH)
    except Exception as e:
        import traceback
        print(f"An error occurred: {e}. You can ignore this error on ODK prepare_release step.")
        print(traceback.format_exc())
    finally:
        if neo_client:
            neo_client.close()


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

# Create a cache with a maximum size of 128 and a TTL of 3600 seconds (1 hour)
cache = TTLCache(maxsize=128, ttl=3600)
ssl._create_default_https_context = ssl._create_unverified_context

@cached(cache)
def get_uberon_label(uberon_curie: str) -> str:
    uberon_id = uberon_curie.strip().replace(":", "_")
    sparql = SPARQLWrapper("https://ubergraph.apps.renci.org/sparql")
    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX obo: <http://purl.obolibrary.org/obo/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT *
    WHERE {{
      obo:{uberon_id} rdfs:label ?label .
    }}
    LIMIT 1
    """.format(uberon_id=uberon_id)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    bindings = results.get("results", {}).get("bindings", [])
    if not bindings:
        raise Exception("Uberon term not found: {}".format(uberon_curie))

    label = bindings[0].get("label", {}).get("value")
    return label


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    subparsers = cli.add_subparsers(help="Available actions", dest="action")

    parser_anndata = subparsers.add_parser("anndata", description="Anndata gene extractor")
    parser_anndata.add_argument("-a", "--anndata", type=str, help="AnnData file path")
    parser_anndata.add_argument("-n", "--namecolumn", type=str, help="AnnData var column name containing gene names")
    parser_anndata.add_argument("-p", "--prefix", type=str, help="Gene ID prefix (such as ensembl or ncbigene)")
    parser_anndata.add_argument("-o", "--out", type=str, help="Output file path")
    parser_anndata.add_argument("-b", "--backed", action="store_true", help="Load AnnData in backed mode for large files")

    parser_genes = subparsers.add_parser("genes", description="Genes template extractor")
    parser_genes.add_argument("-i", "--input", action='append', type=str, help="list of input file paths")
    parser_genes.add_argument("-o", "--out", type=str, help="Output file path")

    parser_cl_genes = subparsers.add_parser("genes_cl", description="Genes used by the CL template extractor")
    parser_cl_genes.add_argument("-i", "--input", action='append', type=str, help="list of input file paths")
    parser_cl_genes.add_argument("-o", "--out", type=str, help="Output file path")

    args = cli.parse_args()

    if args.action == "anndata":
        extract_genes_from_anndata(args.anndata, args.namecolumn, args.prefix, args.out, use_backed=args.backed)
    elif args.action == "genes":
        generate_genes_robot_template(args.input, args.out)
    elif args.action == "genes_cl":
        generate_genes_robot_template(args.input, args.out, agreed=True)
    else:
        print("Invalid action: {}".format(args.action))
        exit(1)
