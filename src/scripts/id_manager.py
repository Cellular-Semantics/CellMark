import os
import pandas as pd
import re


MARKERS_FOLDER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../markers/")


class IDManager:
    def __init__(self, folder_path: str = MARKERS_FOLDER_PATH):
        self.folder_path = folder_path
        self.current_max_id = self._find_max_marker_set()

    def _find_max_marker_set(self):
        max_id = 1000000  # leave some space for manual entries
        pattern = re.compile(r'CLM:(\d{7})')

        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('Source.tsv'):
                file_path = os.path.join(self.folder_path, file_name)
                df = pd.read_csv(file_path, sep='\t')
                for marker_set in df['Marker_set']:
                    match = pattern.match(marker_set)
                    if match:
                        id_value = int(match.group(1))
                        if id_value > max_id:
                            max_id = id_value

        return max_id

    def get_new_id(self):
        self.current_max_id += 1
        return f'CLM:{self.current_max_id:07d}'

    def skip_ids(self, skip_count: int):
        """
        Skip some IDs (probably for manual entries and future use)
        :param skip_count: number of IDs to skip
        :return:
        """
        self.current_max_id += skip_count
