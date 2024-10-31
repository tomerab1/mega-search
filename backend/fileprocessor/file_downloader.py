import asyncio
import typing
import tqdm
from utils import run_command, get_path_without_root


class FileDownloader:
    _MAX_WORKERS = 20

    def __init__(self, file_list: typing.List[str], queue: asyncio.Queue, queue2) -> None:
        self._file_list = file_list
        self._queue = queue
        self._semaphore = asyncio.Semaphore(FileDownloader._MAX_WORKERS)
        self._pbar = tqdm.tqdm(total=len(file_list))

    @property
    def file_list(self) -> typing.List[str]:
        return self._file_list

    async def worker(self):
        async with self._semaphore:
            try:
                file_path = await self._queue.get()
                await run_command(['mega-get', get_path_without_root(file_path), file_path], enable_stderr=False)
                self._pbar.update(1)
            except Exception as e:
                print(f"Error downloading {file_path}: {e}")
            finally:
                self._queue.task_done()

    async def download(self):
        for file in self.file_list:
            await self._queue.put(file)

        tasks: typing.List[asyncio.Task] = []
        for i in range(len(self.file_list)):
            tasks.append(asyncio.create_task(self.worker()))

        await self._queue.join()
        self._pbar.close()

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
