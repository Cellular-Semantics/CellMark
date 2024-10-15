from neo4j import GraphDatabase


class Neo4jClient:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_cell_cluster_iri(self, cluster_name, cxg_dataset):
        with self.driver.session() as session:
            result = session.execute_read(self._find_cell_cluster_iri, cluster_name, cxg_dataset)
            return result

    def get_cell_info(self, cluster_name, cxg_dataset):
        with self.driver.session() as session:
            result = session.execute_read(self._find_cell_info, cluster_name, cxg_dataset)
            return result

    @staticmethod
    def _find_cell_cluster_iri(tx, cluster_name, cxg_dataset):
        """
        Find the iri of a CL_KG cluster with the given name in the given dataset.
        :param tx:
        :param cluster_name: name of the cluster
        :param cxg_dataset: name of the dataset
        :return:
        """
        if cxg_dataset.endswith(".cxg"):
            cxg_dataset = cxg_dataset + "/"
        query = """
        MATCH (n:Cell_cluster) -[]-> (d:Dataset) 
        WHERE toLower(n.label) = toLower($name) AND $cxg_dataset IN d.title 
        RETURN n.iri AS iri
        """
        result = tx.run(query, name=cluster_name, cxg_dataset=cxg_dataset)
        return [record["iri"] for record in result]

    @staticmethod
    def _find_cell_info(tx, cluster_name, cxg_dataset):
        """
        Find the CL term info related with the given CL_KG cluster name in the given dataset.
        :param tx:
        :param cluster_name: name of the cluster
        :param cxg_dataset: name of the dataset
        :return:
        """
        if cxg_dataset.endswith(".cxg"):
            cxg_dataset = cxg_dataset + "/"
        query = """
        MATCH (c:Cell)<-[composed_primarily_of]-(n:Cell_cluster) -[]-> (d:Dataset) 
        WHERE toLower(n.label) = toLower($name) AND $cxg_dataset IN d.title 
        RETURN c.curie AS curie, c.label AS label
        """
        result = tx.run(query, name=cluster_name, cxg_dataset=cxg_dataset)
        records = [record for record in result]
        if records:
            return {"curie": records[0]["curie"], "label": str(records[0]["label"]).replace(",", "")}
        else:
            return {"curie": "", "label": ""}
