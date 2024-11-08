import asyncio
import unicodedata
import logging
import aiofiles
import re
from PIL import Image
import utils
from spire.doc import *
from spire.doc.common import *
import pytesseract
import pdf2image

logger = logging.getLogger(__name__)


class FileProcessor:
    def __init__(self, queue: asyncio.Queue, semaphore: asyncio.Semaphore) -> None:
        self._queue = queue
        self._semaphore = semaphore
        self._handlers = {
            ".pdf": self.handle_pdf,
            ".doc": self.handle_docx,
            ".docx": self.handle_pdf,
            ".txt": self.handle_text_based,
            ".c": self.handle_text_based,
            ".cpp": self.handle_text_based,
            ".h": self.handle_text_based,
            ".hpp": self.handle_text_based,
            ".java": self.handle_text_based,
            ".py": self.handle_text_based,
            ".racket": self.handle_text_based,
        }
        self._loop = asyncio.get_event_loop()

    async def clean_text(self, text: str):
        text = text.replace('\n', ' ').replace(
            '\r', ' ').replace('\t', ' ').replace('|', '')
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'[\u200B-\u200F\uFEFF]', '', text)
        text = ''.join(char for char in text if char.isprintable())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def handle_pdf(self, file_path: str):
        custom_config = r'--oem 3 --psm 6'
        imgs = await self._loop.run_in_executor(None, pdf2image.convert_from_path, file_path)

        all_text = ""
        for _, image in enumerate(imgs):
            text = await self._loop.run_in_executor(None, lambda: pytesseract.image_to_string(image, lang='heb+eng', config=custom_config))
            all_text += await self.clean_text(text) + '\n'

        # Will send the text to the backend api
        async with aiofiles.open("log.txt", "w+") as fw:
            await fw.write(all_text)

    async def handle_docx(self, file_path: str):
        doc = Document()
        doc.LoadFromFile(file_path)
        text = await self._loop.run_in_executor(None, doc.GetText)
        # Will send the text to the backend api

    async def handle_text_based(self, file_path: str):
        text = ""
        async with aiofiles.open(file_path, "r") as f:
            text = await f.read()
        # Will send the text to the backend api

    async def process(self):
        while True:
            try:
                async with self._semaphore:
                    file_path = await self._queue.get()

                    if file_path == "@@Processing$Done@@":
                        break

                    if os.path.exists(file_path) and os.path.getsize(file_path) > utils.as_mb(100):
                        continue

                    file_extension = os.path.splitext(file_path)[-1]
                    handler = self._handlers.get(file_extension)
                    if handler:
                        await handler(file_path)
                    else:
                        logger.error(
                            f"No handler for file extension: {file_extension}")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
            finally:
                self._queue.task_done()
