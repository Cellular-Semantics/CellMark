# How to Run CellMark pipeline

Users are expected to place their data in the `src/markers/input` directory in a standardized format. Additional supplementary material can be placed in the `src/markers/supplementary` directory. The pipeline will generate the output in the `src/markers/raw` directory.

Before running the ODK pipeline, some preparations should be completed (since some libs (neo4j, anndata etc.) are not supported by ODK):

## 1- Check input data

Validate user provided data in the `src/markers/input` directory. The data must have the following columns:

| clusterName | f_score | NSForest_markers | cxg_dataset_title |
|-------------|---------|------------------|-------------------|

In addition to the input data files, the user should provide a supplementary metadata file in the same directory with the same name except with `yaml` extension.

```yaml
Organ: "Lung"
Species: "NCBITaxon:9606"
Species_abbreviation: "Human"
Organ_region: "UBERON:0002048"
Parent: "SO:0001260"
Marker_set_xref: "https://doi.org/10.5281/zenodo.11165918"
CxG_collection: "https://cellxgene.cziscience.com/collections/6f6d381a-7701-4781-935c-db10d30de293"
CxG_dataset: "An integrated cell atlas of the human lung in health and disease (core)"
```

`CxG_dataset` and `CxG_collection` are optional fields. If provided, the pipeline will use them to query CL_KG. If `CxG_dataset` is not provided, the pipeline will use the `cxg_dataset_title` column in the input data file. 

## 2- Prepare Gene DBs

1- Pipeline requires gene databases to be in place. These gene DBs are located at: `src/templates`. Please check `src/templates/LungCellAtlas.tsv` as an example.
2- These DBs are automatically generated from the related anndata files. When a new experiment data is added to the `src/markers/input` directory, its gene DB should be generated.
3- Generation of gene DBs is driven by the `src/markers/Makefile`:
- Mount the shared drive `/Volumes/osumi-sutherland/development` to access anndata files or download the anndata files to the `src/markers` directory
- add DB name (any simple name) to the `GENE_LIST`
- add a rule for that DB:
```bash
$(TEMPLATESDIR)/LungCellAtlas.tsv:
	python $(SCRIPTSDIR)/robot_template_generator.py anndata --anndata 8d84ba15-d367-4dce-979c-85da70b868a2.h5ad --namecolumn original_gene_symbols --prefix ensembl --out $@
```
- run `make` command to generate the DB in the `src/markers` folder
- This will create a new DB file in the `src/templates` folder. Check its content and make sure it is correct.

## 3- Prepare templates source files

Neo4j client cannot be run inside ODK, so we need to prepare the templates source files before running the pipeline. For each input file a source file will be generated in the `src/markers/templates` directory. The source file will be used to generate the final templates.

Source files will only be created if it does not exist. If you want to regenerate the source file, you should delete the existing source file.

Curators should add their CL annotations to the source files (`cl_term` column).

Run the following script to generate the source files:

```bash
pyton src/scripts/dosdp_template_generator.py
```
