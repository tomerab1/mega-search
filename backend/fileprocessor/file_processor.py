import asyncio
import concurrent.futures
import unicodedata
import logging
import re
import os
import utils
import pdfplumber
from typing import List
from PIL import Image
from spire.doc import *
from spire.doc.common import *
import pytesseract
import pdf2image

logger = logging.getLogger(__name__)


class FileProcessor:
    _MAX_WORKERS = 5

    def __init__(self, queue: asyncio.Queue, semaphore: asyncio.Semaphore) -> None:
        self._queue = queue
        self._semaphore = semaphore
        self._handlers = {
            ".pdf": FileProcessor.handle_pdf,
            ".doc": FileProcessor.handle_docx,
            ".docx": FileProcessor.handle_pdf,
            ".txt": FileProcessor.handle_text_based,
            ".c": FileProcessor.handle_text_based,
            ".cpp": FileProcessor.handle_text_based,
            ".h": FileProcessor.handle_text_based,
            ".hpp": FileProcessor.handle_text_based,
            ".java": FileProcessor.handle_text_based,
            ".py": FileProcessor.handle_text_based,
            ".racket": FileProcessor.handle_text_based,
        }

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
            all_text += FileProcessor.clean_text(text) + '\n'

        return all_text

    @staticmethod
    def handle_pdf(file_path: str):
        pages_to_skip = []
        all_text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = FileProcessor.clean_text(page.extract_text())
                if text:
                    all_text += text
                else:
                    pages_to_skip.append(page.page_number)

            # If all the pages where readable text there is not need to perform ocr, will
            if len(pages_to_skip) != len(pdf.pages):
                all_text += FileProcessor.handle_pdf_ocr(
                    file_path, pages_to_skip)

        # Will send the text to the backend api
        with open(f"{file_path.split('/')[-1].split('.')[0]}.txt", "w+") as fw:
            fw.write(all_text)

    @staticmethod
    def handle_docx(file_path: str):
        doc = Document()
        doc.LoadFromFile(file_path)
        text = doc.GetText()
        # Will send the text to the backend api

    @staticmethod
    def handle_text_based(file_path: str):
        text = ""
        with open(file_path, "r") as f:
            text = f.read()
        # Will send the text to the backend api

    async def process(self):
        with concurrent.futures.ProcessPoolExecutor(max_workers=FileProcessor._MAX_WORKERS) as pool:
            tasks: List[concurrent.futures.Future] = []

            while True:
                try:
                    file_path = await self._queue.get()

                    # Exit string from the downloader
                    if file_path == "@@Processing$Done@@":
                        break

                    # Limit file size to 100mb
                    if os.path.exists(file_path) and os.path.getsize(file_path) > utils.as_mb(100):
                        continue

                    file_extension = os.path.splitext(file_path)[-1]
                    handler = self._handlers.get(file_extension)

                    if handler:
                        # upload work to pool
                        future = pool.submit(handler, file_path)
                        tasks.append(future)
                    else:
                        logger.error(
                            f"No handler for file extension: {file_extension}")

                    if len(tasks) >= FileProcessor._MAX_WORKERS:
                        done, tasks = await asyncio.wait(
                            [asyncio.wrap_future(task) for task in tasks],
                            return_when=asyncio.FIRST_COMPLETED
                        )

                        for completed_task in done:
                            try:
                                _ = completed_task.result()
                            except Exception as e:
                                logger.error(f"Error in completed task: {e}")

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                finally:
                    self._queue.task_done()

            await asyncio.gather(*[asyncio.wrap_future(task) for task in tasks])
