## Mount shared drive `/Volumes/osumi-sutherland/development` to access anndata files
## or download the anndata files to the `src/markers` directory
##
## Source files:
## 8bcc7ef5-f08e-49fc-824f-ced6d951138a.h5ad		Human CellCards Multi-Study CellRef 1.0 Atlas (LungMAP)		https://cellxgene.cziscience.com/collections/f86d6317-7215-409e-bfda-3f4ded3dadaa
## 8d84ba15-d367-4dce-979c-85da70b868a2.h5ad		The integrated Human Lung Cell Atlas		https://cellxgene.cziscience.com/collections/6f6d381a-7701-4781-935c-db10d30de293



SCRIPTSDIR=                 ../scripts
TEMPLATESDIR = 				../templates

GENE_LIST = LungMAP LungCellAtlas
GENE_TABLES = $(patsubst %, $(TEMPLATESDIR)/%.tsv, $(GENE_LIST))


all: $(GENE_TABLES)

$(TEMPLATESDIR)/LungMAP.tsv:
	python $(SCRIPTSDIR)/robot_template_generator.py anndata --anndata 8bcc7ef5-f08e-49fc-824f-ced6d951138a.h5ad --namecolumn origSymbol --prefix ensembl --out $@

$(TEMPLATESDIR)/LungCellAtlas.tsv:
	python $(SCRIPTSDIR)/robot_template_generator.py anndata --anndata 8d84ba15-d367-4dce-979c-85da70b868a2.h5ad --namecolumn original_gene_symbols --prefix ensembl --out $@