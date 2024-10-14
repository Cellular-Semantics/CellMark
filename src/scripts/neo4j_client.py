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

    @staticmethod
    def _find_cell_cluster_iri(tx, cluster_name, cxg_dataset):
        # query = """
        # MATCH (n:Cell_cluster)
        # WHERE toLower(n.label) = toLower($name)
        # RETURN n.iri AS iri
        # """
        if cxg_dataset.endswith(".cxg"):
            cxg_dataset = cxg_dataset + "/"
        query = """
        MATCH (n:Cell_cluster) -[]-> (d:Dataset) 
        WHERE toLower(n.label) = toLower($name) AND $cxg_dataset IN d.title 
        RETURN n.iri AS iri
        """
        result = tx.run(query, name=cluster_name, cxg_dataset=cxg_dataset)
        return [record["iri"] for record in result]
