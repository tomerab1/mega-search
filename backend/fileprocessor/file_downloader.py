import asyncio
import typing

from utils import run_command


class FileDownloader:
    def __init__(self, file_list: typing.List[str], queue: asyncio.Queue, queue2) -> None:
        self._file_list = file_list
        self._queue = queue

    @property
    def file_list(self) -> typing.List[str]:
        return self._file_list

    def get_path_without_root(self, path: str) -> str:
        return path[path.index('/') + 1:]

    async def worker(self):
        try:
            file_path = await self._queue.get()
            output = await run_command(['mega-get', self.get_path_without_root(file_path), file_path], enable_stderr=False)
            print(output)
            print(
                f"downloaded {self.get_path_without_root(file_path)} to {file_path}")
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

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
