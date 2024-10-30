import asyncio
import typing

from file_downloader import FileDownloader
from file_processor import FileProcessor


class Coordinatior:
    def __init__(self, file_list: typing.List[str]):
        self._download_queue = asyncio.Queue()
        self._processor_queue = asyncio.Queue()
        self._downloader = FileDownloader(
            file_list, self._download_queue, self._processor_queue)
        self._processor = FileProcessor(self._processor_queue)

    async def start(self):
        await self._downloader.download()
