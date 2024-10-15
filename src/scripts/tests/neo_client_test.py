import unittest
from neo4j_client import Neo4jClient


class Neo4jClientTestCase(unittest.TestCase):

    def test_cluster_iri_query(self):
        client = Neo4jClient("neo4j://172.27.24.69:7687", "", "")
        cluster_name = "Adventitial fibroblasts"
        iris = client.get_cell_cluster_iri(cluster_name, "An integrated cell atlas of the human lung in health and disease (core)")
        self.assertIsNotNone(iris)
        self.assertEqual(1, len(iris))
        self.assertTrue(str(iris[0]).startswith("http://example.org/"))
        print(iris)
        client.close()

    def test_cell_info_query(self):
        client = Neo4jClient("neo4j://172.27.24.69:7687", "", "")
        cluster_name = "Adventitial fibroblasts"
        cell_info = client.get_cell_info(cluster_name, "An integrated cell atlas of the human lung in health and disease (core)")
        self.assertIsNotNone(cell_info)
        self.assertEqual(dict, type(cell_info))
        self.assertEqual("CL:4028006", cell_info["curie"])
        self.assertEqual("alveolar type 2 fibroblast cell", cell_info["label"])
        print(cell_info)
        client.close()


if __name__ == '__main__':
    unittest.main()
