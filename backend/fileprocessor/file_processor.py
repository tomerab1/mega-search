import asyncio
import concurrent.futures
import logging
import os
import utils
from typing import List, Dict
from mega_parser import DirNode
from file_hanlder import FileHandler
from file_sender import FileSender

logger = logging.getLogger(__name__)


class FileProcessor:
    _MAX_WORKERS = 5

    def __init__(self, queue: asyncio.Queue, semaphore: asyncio.Semaphore) -> None:
        self._queue = queue
        self._semaphore = semaphore
        self._handlers = {
            ".pdf": FileHandler.handle_pdf,
            ".doc": FileHandler.handle_docx,
            ".docx": FileHandler.handle_pdf,
            ".txt": FileHandler.handle_text_based,
            ".c": FileHandler.handle_text_based,
            ".cpp": FileHandler.handle_text_based,
            ".h": FileHandler.handle_text_based,
            ".hpp": FileHandler.handle_text_based,
            ".java": FileHandler.handle_text_based,
            ".py": FileHandler.handle_text_based,
            ".racket": FileHandler.handle_text_based,
        }

    async def process(self):
        with concurrent.futures.ProcessPoolExecutor(max_workers=FileProcessor._MAX_WORKERS) as pool:
            tasks: List[concurrent.futures.Future] = []
            path_to_file: Dict[str, DirNode] = dict()

            while True:
                try:
                    file: DirNode = await self._queue.get()
                    file_path = file.abs_name

                    path_to_file[file_path] = file

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

                    done, _ = await asyncio.wait(
                        [asyncio.wrap_future(task) for task in tasks],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    to_send = []
                    for completed_task in done:
                        try:
                            path, content = completed_task.result()
                            to_send.append((path_to_file[path], content))
                        except Exception as e:
                            logger.error(f"Error in completed task: {e}")

                    FileSender.send_docs(to_send, path_to_file)

                    # Remove tasks that are done.
                    tasks = [task for task in tasks if not task.done()]

                except Exception as e:
                    print(f"in failure {file}")
                    logger.error(f"Error processing {file_path}: {e}")
                finally:
                    self._queue.task_done()

            await asyncio.gather(*[asyncio.wrap_future(task) for task in tasks])
