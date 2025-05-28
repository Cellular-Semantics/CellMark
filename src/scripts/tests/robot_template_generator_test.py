import unittest
from robot_template_generator import get_uberon_label

class RobotTemplatesTestCase(unittest.TestCase):

    def test_get_uberon_label(self):
        self.assertEqual("lung", get_uberon_label("UBERON:0002048"))


if __name__ == '__main__':
    unittest.main()
