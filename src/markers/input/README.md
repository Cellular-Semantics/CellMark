# How to Add New Markers

To contribute new marker data, please submit a pull request with the appropriate files added to this folder. This will automatically trigger a set of GitHub Actions to validate the data and report any issues.

## 1. Prepare Your Input Data

Place your marker data file(s) in the `src/markers/input` directory. Each file must include the following required columns:

| clusterName | f_score | NSForest_markers | cxg_dataset_title |
|-------------|---------|------------------|-------------------|

You may include additional columns if needed. See NS-Forest SOP [here](https://docs.google.com/document/d/1gkBGF5EIATI_ki0hRjC99irbr7dsuLFk/edit).

## 2. Add Metadata

Alongside the input data, include a corresponding metadata entry in the `src/markers/input/metadata.csv` file. Each row should describe one input file and should include the following fields:

| file_name | Species | Species_abbreviation | Organ_region | Parent | Marker_set_xref | CxG_collection | CxG_dataset |
|-----------|---------|------------------------|----------------|---------|--------------------|------------------|---------------|

Example metadata:

| file_name | Species | Species_abbreviation | Organ_region | Parent | Marker_set_xref | CxG_collection | CxG_dataset |
|-----------|---------|------------------------|----------------|---------|--------------------|------------------|---------------|
| HLCA_CellRef_MarkerPerformance_forDOS.csv | NCBITaxon:9606 | Human | UBERON:0002048 | SO:0001260 | https://doi.org/10.5281/zenodo.11165918 | https://cellxgene.cziscience.com/collections/6f6d381a-7701-4781-935c-db10d30de293 | *An integrated cell atlas of the human lung in health and disease (core)* |
| nsforest_human_neocortex_global_cluster_combinatorial_results.csv | NCBITaxon:9606 | Human | UBERON:0001950 | SO:0001260 | https://doi.org/10.5281/zenodo.11165918 | https://cellxgene.cziscience.com/collections/d17249d2-0e6e-4500-abb8-e6c93fa1ac6f | |
| nsforest_human_neocortex_global_subclass_results.csv | NCBITaxon:9606 | Human | UBERON:0001950 | SO:0001260 | https://doi.org/10.5281/zenodo.11165918 | https://cellxgene.cziscience.com/collections/d17249d2-0e6e-4500-abb8-e6c93fa1ac6f | |

### Notes:
- `CxG_dataset` and `CxG_collection` are optional. If provided, the pipeline will use them to query the CL_KG.
- If `CxG_dataset` is omitted, the pipeline will default to the `cxg_dataset_title` in the input file.

## 3. GitHub Action: Validate Input
After adding your files and metadata, create a pull request. This will trigger an automated GitHub Action that validates the metadata and input files. The action will check for:

- Correct column names and types in the input files.
- Consistency between the input files and the metadata.

<img src="../../../docs/images/github_action_validate_input.png" alt="GitHub Action Validate Input" width="600"/>
