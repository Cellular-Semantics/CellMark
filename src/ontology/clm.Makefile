## Customize Makefile settings for clm
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile
MARKERSDIR = $(SRC)/markers
TEMPLATESDIR = $(SRC)/templates

PYTHON_REQUIREMENTS = $(RELEASEDIR)/requirements.txt

SOURCE_TABLE = $(MARKERSDIR)/NSForestMarkersSource.tsv

GENE_LIST = LungMAP LungCellAtlas
GENE_TABLES = $(patsubst %, $(MIRRORDIR)/%.tsv, $(GENE_LIST))
#GENE_ONTS = $(patsubst %, $(MIRRORDIR)/%.owl, $(GENE_LIST))
GENE_TEMPLATE = $(TEMPLATESDIR)/genes.tsv
GENE_IMPORT_MODULE = $(IMPORTDIR)/genes.owl
#GENE_TERMS = $(TMPDIR)/gene_terms.txt

LOCAL_CLEAN_FILES = $(GENE_IMPORT_MODULE) $(GENE_TEMPLATE)

# clean previous build files
.PHONY: clean_files
clean_files:
	rm -f $(LOCAL_CLEAN_FILES)

.PHONY: install_requirements
install_requirements: $(PYTHON_REQUIREMENTS)
	pip install -r $<

$(MIRRORDIR)/LungMAP.tsv: install_requirements
	python $(SCRIPTSDIR)/robot_template_generator.py anndata --anndata 8bcc7ef5-f08e-49fc-824f-ced6d951138a.h5ad --namecolumn origSymbol --prefix ensembl --out $@

$(MIRRORDIR)/LungCellAtlas.tsv: install_requirements
	python $(SCRIPTSDIR)/robot_template_generator.py anndata --anndata 8d84ba15-d367-4dce-979c-85da70b868a2.h5ad --prefix ncbigene --out $@

$(GENE_TEMPLATE): $(GENE_TABLES)
	python $(SCRIPTSDIR)/robot_template_generator.py genes $(patsubst %, -i %, $^) --out $@

$(GENE_IMPORT_MODULE): $(GENE_TEMPLATE)
	$(ROBOT) template --input $(SRC) --template $< --add-prefixes template_prefixes.json --output $@

$(COMPONENTSDIR)/all_templates.owl: clean_files $(SRC) $(GENE_IMPORT_MODULE)
	$(ROBOT) merge --input $(SRC) --input $(GENE_IMPORT_MODULE) --output $@

.PRECIOUS: $(COMPONENTSDIR)/all_templates.owl

## DOSDP rules override to support template_prefixes
$(DOSDP_OWL_FILES_DEFAULT): $(EDIT_PREPROCESSED) $(DOSDP_TSV_FILES_DEFAULT) $(ALL_PATTERN_FILES) auto_dosdp_templates
	if [ $(PAT) = true ] && [ "${DOSDP_PATTERN_NAMES_DEFAULT}" ]; then $(DOSDPT) generate --catalog=$(CATALOG) \
    --infile=$(PATTERNDIR)/data/default/ --template=$(PATTERNDIR)/dosdp-patterns --batch-patterns="$(DOSDP_PATTERN_NAMES_DEFAULT)" \
    --ontology=$< --obo-prefixes=true --prefixes=template_prefixes.yaml --outfile=$(PATTERNDIR)/data/default; fi

.PHONY: auto_dosdp_%
auto_dosdp_%:
	python $(SCRIPTSDIR)/dosdp_template_generator.py generate --template $* --out ../patterns/data/default/$*.tsv

.PHONY: auto_dosdp_templates
auto_dosdp_templates: auto_dosdp_NSForestMarkers auto_dosdp_MarkersToCells

# override since original rule filter out CL terms
$(ONT)-base.owl: $(EDIT_PREPROCESSED) $(OTHER_SRC)
	$(ROBOT_RELEASE_IMPORT_MODE_BASE) \
	reason --reasoner ELK --equivalent-classes-allowed asserted-only --exclude-tautologies structural --annotate-inferred-axioms False \
	relax \
	reduce -r ELK \
	$(SHARED_ROBOT_COMMANDS) \
	annotate --link-annotation http://purl.org/dc/elements/1.1/type http://purl.obolibrary.org/obo/IAO_8000001 \
		--ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
		--output $@.tmp.owl && mv $@.tmp.owl $@