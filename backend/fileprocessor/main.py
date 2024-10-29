import typing
from enum import Enum
import os
import asyncio

folder_url = 'https://mega.nz/folder/0Sg0iD4B#0OPF1JJgFjtYoJuStlsCtA'


async def run_command(command: typing.List[str], input_text: str = None, enable_stderr: bool = True):
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        proc_input = input_text.encode() if input_text else None

        stdout, stderr = await process.communicate(input=proc_input)

        if enable_stderr and stderr:
            print(f"Error running {' '.join(command)}: {stderr}")

        return stdout.decode()
    except Exception as e:
        print(f"Exception while running {' '.join(command)}: {e}")
        return None


class DirNodeType(Enum):
    Dir = 0
    File = 1


class DirNode:
    def __init__(self, abs_name: str, type: DirNodeType) -> None:
        self._abs_name = abs_name
        self._rel_name = os.path.split(abs_name)[-1]
        self._children: typing.List['DirNode'] = []
        self._type = type

    @property
    def type(self) -> DirNodeType:
        return self._type

    @type.setter
    def type(self, type: DirNodeType) -> None:
        self._type = type

    @property
    def abs_name(self) -> str:
        return self._abs_name

    @abs_name.setter
    def abs_name(self, name: str) -> None:
        self._abs_name = name

    @property
    def rel_name(self) -> str:
        return self._rel_name

    @rel_name.setter
    def rel_name(self, name: str) -> None:
        self._abs_name = name

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, children) -> None:
        self._children = children

    def add_child(self, child: 'DirNode'):
        self._children.append(child)

    def pprint(self, level=0) -> str:
        indent = "  " * level
        result = f"{indent}- {self._rel_name}\n"

        for child in self._children:
            result += child.pprint(level + 1)

        return result

    def __str__(self) -> str:
        return f"({self.abs_name}, {self.type.name})"


class DirTree:
    def __init__(self, root: str) -> None:
        self._root = DirNode(root, DirNodeType.Dir)
        self._dfs_stack = [self._root]

    @property
    def root(self) -> DirNode:
        return self._root

    def __iter__(self):
        self._dfs_stack = [self._root]
        return self

    def __next__(self) -> DirNode:
        if not self._dfs_stack:
            raise StopIteration

        current = self._dfs_stack.pop()
        self._dfs_stack.extend(current.children)
        return current

    def pprint(self) -> str:
        print(self._root.pprint())


class MegaParserSettings:
    def __init__(self, file_postfixes: typing.List[str], allowed_dirs: typing.List[str] | None = None) -> None:
        self._postfixes = file_postfixes
        self._allowed_dirs = allowed_dirs

    @property
    def file_postfixes(self):
        return self._postfixes

    @property
    def allowed_dirs(self):
        return self._allowed_dirs


class MegaResultTokenType(str, Enum):
    Dir = "dir"
    File = "file"
    Skip = "skip"


class MegaResultLexer:
    def __init__(self, text: str, settings: MegaParserSettings) -> None:
        self._settings = settings
        self._lines = text.splitlines()
        self._pos = 0

    # return the type of the node, content and indent level
    def __next__(self) -> typing.Tuple[MegaResultTokenType, str, int]:
        if self._pos >= len(self._lines):
            raise StopIteration

        line = self._lines[self._pos]
        file_parts = os.path.splitext(line)
        extension = file_parts[-1]
        self._pos += 1

        if extension:
            if any([postfix in line for postfix in self._settings.file_postfixes]):
                return MegaResultTokenType.File, line.strip(), line.count('\t')
            else:
                return MegaResultTokenType.Skip, None, -1

        return MegaResultTokenType.Dir, line.strip(), line.count('\t')

    def __iter__(self):
        self._pos = 0
        return self


class MegaResultParser:
    def __init__(self, root_name: str, text: str, settings: MegaParserSettings) -> None:
        self._settings = settings
        self._lexer = MegaResultLexer(text, settings)
        self._tree = DirTree(root_name)

    def parse(self) -> DirTree:
        stack = [(self._tree.root, -1)]

        for token in self._lexer:
            token_type, content, indent_lvl = token

            if token_type is MegaResultTokenType.Skip:
                continue

            while stack and stack[-1][1] >= indent_lvl:
                stack.pop()

            parent_node = stack[-1][0]
            node_type = DirNodeType.Dir if token_type is MegaResultTokenType.Dir else DirNodeType.File

            abs_name = os.path.join(parent_node.abs_name, content)

            # Only take allowed dirs, ignore those that are no in the list.
            if self._settings.allowed_dirs:
                if not any([allowed_dir in abs_name for allowed_dir in self._settings.allowed_dirs]):
                    continue

            new_node = DirNode(abs_name, node_type)
            parent_node.add_child(new_node)

            if token_type is MegaResultTokenType.Dir:
                stack.append((new_node, indent_lvl))

        return self._tree


# Class for file processing, will extract the text out of the files.
class FileProcessor:
    def __init__(self, queue: asyncio.Queue) -> None:
        pass

# Class for downloading files, create 'mega-get' process that will download the files.
class FileDownloader:
    def __init__(self, file_list: typing.List[str], queue: asyncio.Queue) -> None:
        self._file_list = file_list
        self._queue = queue
    
    @property
    def file_list(self) -> typing.List[str]:
        return self._file_list
    
    async def worker(self):
        file_path = await self._queue.get()

        await run_command(['mega-get', file_path[3:], file_path], enable_stderr=False)
        print('downloaded', file_path)
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
        
        await asyncio.gather(*task, return_exceptions=True)
    
class Coordinatior:
    def __init__(self, file_list: typing.List[str]):
        self._queue = asyncio.Queue()
        self._downloader = FileDownloader(file_list, self._queue)
        self._processor = FileProcessor(self._queue)
        
    async def start(self):
        await self._downloader.download()


async def main():
    is_logged_in = False

    if not os.path.exists('dir_names.txt'):
        is_logged_in = True
        await run_command(["mega-cmd"], f"login {folder_url}")

        stdout = await run_command(["mega-ls", "-r"])
        folders = stdout.splitlines()

        with open("dir_names.txt", "w") as fw:
            fw.write('\n'.join(folders))

    with open("files.txt", "w") as fw, open("dir_names.txt", "r") as dn_file:
        text = dn_file.read()
        parser = MegaResultParser(
            "CS",
            text,
            MegaParserSettings([".txt", ".pdf", ".doc"], ["04101 - אשנב למתמטיקה"]))

        tree = parser.parse()

        dir_list = list(map(lambda node: node.abs_name, filter(
            lambda node: node.type is DirNodeType.Dir, tree)))

        await asyncio.gather(*(asyncio.to_thread(os.makedirs, dir, exist_ok=True) for dir in dir_list))

        file_list = list(map(lambda node: node.abs_name, filter(
            lambda node: node.type is DirNodeType.File, tree)))

        for file in file_list:
            fw.write(file + "\n")
            
        coord = Coordinatior(file_list)
        await coord.start()

        if is_logged_in:
            await run_command(["mega-logout"])


if __name__ == "__main__":
    asyncio.run(main())
