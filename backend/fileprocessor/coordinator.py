import asyncio
import typing

from file_downloader import FileDownloader
from file_processor import FileProcessor
from mega_parser import DirNode


class Coordinatior:
    _MAX_CONCURRENT_TASKS = 1024

    def __init__(self, file_list: typing.List[DirNode]):
        self._download_queue = asyncio.Queue()
        self._processor_queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(Coordinatior._MAX_CONCURRENT_TASKS)
        self._downloader = FileDownloader(
            file_list,
            self._download_queue,
            self._processor_queue,
            self._semaphore)
        self._processor = FileProcessor(self._processor_queue, self._semaphore)

    async def start(self):
        processor = self._processor.process()
        downloader = self._downloader.download()

        await asyncio.gather(processor, downloader, return_exceptions=True)
