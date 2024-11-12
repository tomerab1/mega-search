import asyncio
import typing
import tqdm
from mega_parser import DirNode
from utils import run_command, get_path_without_prefix


class FileDownloader:
    def __init__(self,
                 file_list: typing.List[DirNode],
                 queue: asyncio.Queue,
                 file_processor_queue: asyncio.Queue,
                 semaphore: asyncio.Semaphore) -> None:
        self._file_list = file_list
        self._queue = queue
        self._file_processor_queue = file_processor_queue
        self._semaphore = semaphore
        self._pbar = tqdm.tqdm(total=len(file_list))

    @property
    def file_list(self) -> typing.List[DirNode]:
        return self._file_list

    async def worker(self):
        async with self._semaphore:
            try:
                file: DirNode = await self._queue.get()
                file_path = file.abs_name
                await run_command(['mega-get', get_path_without_prefix(file_path, "data/CS"), file_path], enable_stderr=False)
                # publish work to the file processor queue
                await self._file_processor_queue.put(file)
                self._pbar.update(1)
            except Exception as e:
                print(f"Error downloading {file_path}: {e}")
            finally:
                self._queue.task_done()

    async def download(self):
        for file in self.file_list:
            await self._queue.put(file)

        tasks: typing.List[asyncio.Task] = []
        for _ in range(len(self.file_list)):
            tasks.append(asyncio.create_task(self.worker()))

        await self._queue.join()
        self._pbar.close()

        await self._file_processor_queue.put(DirNode("@@Processing$Done@@", None, None))
        await self._file_processor_queue.join()

        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
