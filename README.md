
![Build Status](https://github.com/Cellular-Semantics/CellMark/actions/workflows/qc.yml/badge.svg)
# Cell Markers Ontology

An ontology of cell type markers.

This ontology integrates cell type markers for cells in the [Cell Ontology](https://github.com/obophenotype/cell-ontology) from various sources along with details of marker context (anatomical context, assay), confidence (where available) and provenance.   

This ontology is not currently registered with or approved by the OBO foundry.  It is intended, primarily, as a source for the content for the [CL knowledge graph](https://github.com/Cellular-Semantics/CL_KG/).

## Schema

The ontology captures the following key concepts:
<img width="1021" height="372" alt="image" src="https://github.com/user-attachments/assets/03431491-14c8-4b55-8f0f-adf55e9183af" />

## Adding New Marker Files

To add new marker files, follow these steps:

- **Create a New Branch**: Create a new branch in your repository for your changes.
- **Prepare Input Data**: Add your marker data file(s) to the `src/markers/input` directory. Ensure the file includes the required columns: `clusterName`, `f_score`, `NSForest_markers`, and `cxg_dataset_title`.
- **Add Metadata**: Update the `src/markers/input/metadata.csv` file with a new row describing your input file. Include fields like `file_name`, `Organ_region`, `Species`, and others as specified in the detailed guide.
- **Create a Pull Request**: Open a pull request to merge your branch into the main repository. This will trigger GitHub Actions to validate your input files and metadata.

For more details, refer to the [Quick Start Guide](docs/add_new_markers_quick.md) or the [Detailed Data Upload Guide](src/markers/input/README.md).

## Running the Pipeline (For Admins)

Admins responsible for running the pipeline should follow the instructions provided in the [Pipeline Guide](src/ontology/README-run-pipeline.md).

### Overview:

General workflow can be found at [Workflow Documentation](docs/pipeline_workflow.md).

### Key Steps:
- **Prepare Input Data**: Ensure that the input data and metadata in the `src/markers/input` directory are validated and meet the required format.
- **Prepare Gene Databases**: Generate gene databases from the provided anndata files using the `Makefile` in `src/markers`.
- **Generate Source Files**: Use the `dosdp_template_generator.py` script to create or update source files for input data.
- **Prepare QuickGO Templates**: Run the `go_term_template_generator.py` script to fetch and prepare Gene Ontology templates.
- **Prepare CellxGene Marker Templates**: Run the `cellxgene_marker_template_generator.py` 
  script to download marker data, resolve UBERON/NCBITaxon/NCBIgene URIs, filter and cap markers,
  and prepare a ROBOT TSV (`cellxgene_marker_template.tsv`) in `src/templates/cl_kg/`.
- **Run the ODK Pipeline**: Execute the pipeline using the `make prepare_release` command as described in the guide.


Refer to the [Pipeline Guide](src/ontology/README-run-pipeline.md) for detailed instructions and additional context.

## Contact

Please use this GitHub repository's [Issue tracker](https://github.com/Cellular-Semantics/CellMark/issues) to request new content or report errors or specific concerns related to the ontology.
