import unicodedata
import logging
import re
import pdfplumber
from typing import List, Dict, Tuple
from PIL import Image
from spire.doc import *
from spire.doc.common import *
import pytesseract
import pdf2image
from mega_parser import DirNode

logger = logging.getLogger(__name__)


class FileHandler:
    @staticmethod
    def clean_text(text: str):
        text = text.replace('\n', ' ').replace(
            '\r', ' ').replace('\t', ' ').replace('|', '')
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'[\u200B-\u200F\uFEFF]', '', text)
        text = ''.join(char for char in text if char.isprintable())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def handle_pdf_ocr(file_path: str, pages_to_skip: List[int]):
        custom_config = r'--oem 3 --psm 6'
        imgs = pdf2image.convert_from_path(file_path)

        all_text = ""
        for i, image in enumerate(imgs):
            if (i + 1) in pages_to_skip:
                continue
            text = pytesseract.image_to_string(
                image, lang='heb+eng', config=custom_config)
            all_text += FileHandler.clean_text(text) + '\n'

        return all_text

    @staticmethod
    def handle_pdf(file_path: str) -> Tuple[str, str]:
        pages_to_skip = []
        all_text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = FileHandler.clean_text(page.extract_text())
                if text:
                    all_text += text
                else:
                    pages_to_skip.append(page.page_number)

            # If all the pages where readable text there is not need to perform ocr, will
            if len(pages_to_skip) != len(pdf.pages):
                all_text += FileHandler.handle_pdf_ocr(
                    file_path, pages_to_skip)

        return (file_path, all_text)

    @staticmethod
    def handle_docx(file_path: str) -> Tuple[str, str]:
        doc = Document()
        doc.LoadFromFile(file_path)
        return (file_path, doc.GetText())

    @staticmethod
    def handle_text_based(file_path: str) -> Tuple[str, str]:
        text = ""
        with open(file_path, "r") as f:
            text = f.read()

        return (file_path, text)

    @staticmethod
    def send_docs(to_send: List[Tuple[DirNode, str]], mapping: Dict[str, DirNode]):
        # requests.post('localhost:8080/upload')

        for node, conent in to_send:
            print(f"sended {node} removing {node.abs_name}")
            del mapping[node.abs_name]
