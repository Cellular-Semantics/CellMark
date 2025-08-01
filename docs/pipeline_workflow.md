# Ontology Pipeline Workflow

Workflow for the Cell Markers Ontology (CLM) pipeline, detailing the steps involved in preparing and running the ontology generation process. Further details can be found in the [pipeline README](../src/ontology/README-run-pipeline.md).

## 1. Input Data Preparation
- Users provide input data files in a standardized format in the `src/markers/input` directory.
- Metadata for these files is added to `src/markers/input/metadata.csv`.
- A GitHub Action validates the input files and metadata.
- see [Adding New Marker Files](add_new_markers_quick.md) for details on the required columns and format.

## 2. Input Data Processing

### Gene DB Preparation

- `src/markers/Makefile` is used to generate the Gene DBs.
- Anndata files are either manually downloaded or mounted from a shared drive and genes are extracted from AnnData `var`. A ROBOT template is generated for the genes in the `src/templates` directory.

### Source Files Generation
- Neo4j client cannot be run inside ODK, so we need to prepare the templates source files before running the pipeline.
- _Note: You should be connected to the Sanger intranet to be able to run the Neo4j queries._
- Run `python src/scripts/dosdp_template_generator.py`
- For each input file, a source file is generated in the `src/markers/$input_file_name$Source.tsv`.
- Also, queries the CL_KG to retrieve the auto-generated IDs of the Clusters for each used cxg_dataset. CL_KG Clusters individuals template is generated at `src/templates/cl_kg/Clusters.tsv`. 
- CK_KG Cluster individuals has auto-generated IDs. So this template should be regenerated with each CL_KG update.

## 3. Editor Curation
- Editors manually check the generated source files (`src/markers/$input_file_name$Source.tsv`) and annotates to determine if the terms will be added to the Cell Ontology.

## 4. QuickGO Template Generation
- The `go_term_template_generator.py` script retrieves Gene Ontology (GO) terms from a Neo4j database, fetches additional data from the QuickGO API, and converts the data into ROBOT templates for use in the CLM ontology pipeline.
- It processes the data into ROBOT templates, which are saved in the `src/templates/cl_kg/` directory.
- This step is optional and only run when new GO terms are needed.
<img width="736" height="347" alt="image" src="https://github.com/user-attachments/assets/7c36df82-f243-4847-a0d6-89ef2c88dfb2" />

## 5. CellxGene Marker Template Generation
- The `cellxgene_marker_template_generator.py` script downloads and parses marker–gene JSON data from the CxG (cellxgene) service, then:
  1. Looks up UBERON and NCBITaxon URIs via SPARQL.  
  2. Resolves gene labels to NCBI Gene URIs via the MyGene.info API (with a simple cache).  
  3. Filters markers by score threshold and caps at 7 entries per CL term.  
  4. Writes out a remapped JSON (`new_marker.json`).  
  5. Generates a ROBOT template TSV (`cellxgene_marker_template.tsv`) in the `src/templates/cl_kg/` directory for OWL template processing.
- This step is **optional**, and should be run whenever you need to regenerate templates for new or updated CellxGene marker data.
<img width="1119" height="398" alt="image" src="https://github.com/user-attachments/assets/743012af-a8cd-488e-9187-ba15a35e3872" />

## 6. Run ODK Pipeline

- The ODK pipeline is executed to generate the final ontology files.
- `cd src/onotology & sh run.sh make prepare_release`
- Pipeline automatically merges the source files into an intermediate `NSForestMarkersSource.tsv` file.
- Using the `NSForestMarkersSource.tsv` file, generates dosdp template files at `src/patterns/data/default`
- Merges the Gene DB templates and generates two gene ontologies subsets to be merged into the `cml-kg.owl` and `clm-cl.owl` files.
- Runs dosdp and robot templates to generate ontologies.

## 7. CLM Ontology in Use
- A pipeline in the Cell Ontology repository uses the `clm-cl.owl` ontology to generate the final ontology files.
- Another pipeline in the CL_KG repository uses the `cml-kg.owl` ontology to generate the knowledge graph.

# Summary
The project automates the process of integrating biological data, generating ontology templates, and producing ontology files for use in research or applications.
