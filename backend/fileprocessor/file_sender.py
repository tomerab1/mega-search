import requests
import logging
from typing import List, Tuple, Dict
from mega_parser import DirNode

logger = logging.getLogger(__name__)


class FileSender:
    @staticmethod
    def send_docs(to_send: List[Tuple[DirNode, str]], mapping: Dict[str, DirNode]):
        # requests.post('localhost:8080/upload')

        for node, conent in to_send:
            print(f"sended {node} removing {node.abs_name}")
            del mapping[node.abs_name]
