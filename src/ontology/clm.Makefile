## Customize Makefile settings for clm
## 
## If you need to customize your Makefile, make
## changes here rather than in the main Makefile

## NOTE: This make file depends on the output of the ../markers/Makefile
## Run it first to prepare the necessary gene template files from scratch if needed

MARKERSDIR = ../markers
TEMPLATESDIR = ../templates

#SOURCE_TABLE = $(MARKERSDIR)/NSForestMarkersSource.tsv

GENE_LIST = LungMAP LungCellAtlas Neocortex
GENE_TABLES = $(patsubst %, $(TEMPLATESDIR)/%.tsv, $(GENE_LIST))
GENE_TEMPLATE = $(TEMPLATESDIR)/genes.tsv
GENE_TEMPLATE_CL = $(TEMPLATESDIR)/genes_cl.tsv

LOCAL_CLEAN_FILES = $(GENE_TEMPLATE) $(GENE_TEMPLATE_CL) $(PATTERNDIR)/data/default/NSForestMarkers_all.tsv $(PATTERNDIR)/data/default/MarkersToCells_all.tsv

# clean previous build files
.PHONY: clean_files
clean_files:
	rm -f $(LOCAL_CLEAN_FILES)

$(GENE_TEMPLATE): $(GENE_TABLES)
	python $(SCRIPTSDIR)/robot_template_generator.py genes $(patsubst %, -i %, $^) --out $@

$(GENE_TEMPLATE_CL): $(GENE_TABLES)
	python $(SCRIPTSDIR)/robot_template_generator.py genes_cl $(patsubst %, -i %, $^) --out $@

$(MIRRORDIR)/genes.owl: $(GENE_TEMPLATE)
	$(ROBOT) template --input $(SRC) --template $< --add-prefixes template_prefixes.json --output $@

$(MIRRORDIR)/genes_cl.owl: $(GENE_TEMPLATE_CL)
	$(ROBOT) template --input $(SRC) --template $< --add-prefixes template_prefixes.json --output $@

$(COMPONENTSDIR)/all_templates.owl: clean_files
	#$(ROBOT) merge --input $(SRC) --input $(GENE_IMPORT_MODULE) --output $@
	echo "Templates ready"

.PRECIOUS: $(COMPONENTSDIR)/all_templates.owl

## DOSDP rules override to support template_prefixes
$(DOSDP_OWL_FILES_DEFAULT): $(EDIT_PREPROCESSED) $(DOSDP_TSV_FILES_DEFAULT) $(ALL_PATTERN_FILES) clean_files auto_dosdp_templates
	if [ $(PAT) = true ] && [ "${DOSDP_PATTERN_NAMES_DEFAULT}" ]; then $(DOSDPT) generate --catalog=$(CATALOG) \
    --infile=$(PATTERNDIR)/data/default/ --template=$(PATTERNDIR)/dosdp-patterns --batch-patterns="$(DOSDP_PATTERN_NAMES_DEFAULT)" \
    --ontology=$< --obo-prefixes=true --prefixes=template_prefixes.yaml --outfile=$(PATTERNDIR)/data/default; fi

.PHONY: auto_dosdp_%
auto_dosdp_%:
	python $(SCRIPTSDIR)/dosdp_template_generator.py generate --template $* --agreed --out ../patterns/data/default/$*.tsv

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

# Release additional artifacts
$(ONT).owl: $(ONT)-full.owl $(ONT)-kg.owl $(ONT)-kg.obo $(ONT)-kg.json $(ONT)-cl.owl $(ONT)-cl.obo $(ONT)-cl.json
	$(ROBOT) annotate --input $< --ontology-iri $(URIBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
		convert -o $@.tmp.owl && mv $@.tmp.owl $@
	rm -f $(LOCAL_CLEAN_FILES)

# Artifact for KG that host not validated gene annotations as well
$(ONT)-kg.owl:  $(ONT)-base.owl $(MIRRORDIR)/genes.owl
	python $(SCRIPTSDIR)/dosdp_template_generator.py generate --template NSForestMarkers --out $(PATTERNDIR)/data/default/NSForestMarkers_all.tsv
	$(DOSDPT) generate --catalog=$(CATALOG) --infile=$(PATTERNDIR)/data/default/NSForestMarkers_all.tsv --template=$(PATTERNDIR)/dosdp-patterns/NSForestMarkers.yaml \
		--ontology=$(EDIT_PREPROCESSED) --obo-prefixes=true --prefixes=template_prefixes.yaml --outfile=$(COMPONENTSDIR)/NSForestMarkers_all.owl
	$(ROBOT) template --input $(SRC) --template $(TEMPLATEDIR)/cl_kg/Clusters.tsv --add-prefixes template_prefixes.json --output $(COMPONENTSDIR)/MarkersToCells_all.owl
	$(ROBOT) merge -i $< -i $(ONT)-kg-edit.$(EDIT_FORMAT) -i $(MIRRORDIR)/genes.owl -i $(COMPONENTSDIR)/NSForestMarkers_all.owl -i $(COMPONENTSDIR)/MarkersToCells_all.owl \
	 	annotate --ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
		--output $(RELEASEDIR)/$@

$(ONT)-kg.obo: $(RELEASEDIR)/$(ONT)-kg.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo && grep -v ^owl-axioms $@.tmp.obo > $(RELEASEDIR)/$@ && rm $@.tmp.obo

$(ONT)-kg.json: $(RELEASEDIR)/$(ONT)-kg.owl
	$(ROBOT) annotate --input $< --ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
		convert --check false -f json -o $@.tmp.json &&\
	jq -S 'walk(if type == "array" then sort else . end)' $@.tmp.json > $(RELEASEDIR)/$@ && rm $@.tmp.json


# Artifact for CL that hosts only the validated gene annotations
$(ONT)-cl.owl: $(ONT)-base.owl $(MIRRORDIR)/genes_cl.owl
	$(ROBOT) merge -i $< -i $(MIRRORDIR)/genes_cl.owl \
	 	annotate --ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
		--output $(RELEASEDIR)/$@

$(ONT)-cl.obo: $(RELEASEDIR)/$(ONT)-cl.owl
	$(ROBOT) convert --input $< --check false -f obo $(OBO_FORMAT_OPTIONS) -o $@.tmp.obo && grep -v ^owl-axioms $@.tmp.obo > $(RELEASEDIR)/$@ && rm $@.tmp.obo

$(ONT)-cl.json: $(RELEASEDIR)/$(ONT)-cl.owl
	$(ROBOT) annotate --input $< --ontology-iri $(ONTBASE)/$@ $(ANNOTATE_ONTOLOGY_VERSION) \
		convert --check false -f json -o $@.tmp.json &&\
	jq -S 'walk(if type == "array" then sort else . end)' $@.tmp.json > $(RELEASEDIR)/$@ && rm $@.tmp.json