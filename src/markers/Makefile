SCRIPTSDIR=                 ../scripts
MIRRORDIR=                  ../ontology/mirror

GENE_LIST = LungMAP LungCellAtlas
GENE_TABLES = $(patsubst %, $(MIRRORDIR)/%.tsv, $(GENE_LIST))


all: $(GENE_TABLES)

$(MIRRORDIR)/LungMAP.tsv:
	python $(SCRIPTSDIR)/robot_template_generator.py anndata --anndata 8bcc7ef5-f08e-49fc-824f-ced6d951138a.h5ad --prefix ncbigene --out $@

$(MIRRORDIR)/LungCellAtlas.tsv:
	python $(SCRIPTSDIR)/robot_template_generator.py anndata --anndata 8d84ba15-d367-4dce-979c-85da70b868a2.h5ad --prefix ncbigene --out $@