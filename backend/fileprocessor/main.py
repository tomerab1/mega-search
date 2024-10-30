import os
import asyncio

from coordinator import Coordinatior
from utils import run_command
from mega_parser import DirNodeType, MegaParserSettings, MegaResultParser

folder_url = 'https://mega.nz/folder/0Sg0iD4B#0OPF1JJgFjtYoJuStlsCtA'


async def main():
    await run_command(["mega-cmd"], f"login {folder_url}")

    if not os.path.exists('dir_names.txt'):
        stdout = await run_command(["mega-ls", "-r"])
        folders = stdout.splitlines()

        with open("dir_names.txt", "w") as fw:
            fw.write('\n'.join(folders))

    if not os.path.exists('files.txt'):
        with open("files.txt", "w") as fw, open("dir_names.txt", "r") as dn_file:
            text = dn_file.read()
            parser = MegaResultParser(
                "CS",
                text,
                MegaParserSettings([".txt", ".pdf", ".doc"], ["04101 - אשנב למתמטיקה/Mamans"]))

            tree = parser.parse()

            dir_list = list(map(lambda node: node.abs_name, filter(
                lambda node: node.type is DirNodeType.Dir, tree)))

            await asyncio.gather(*(asyncio.to_thread(os.makedirs, dir, exist_ok=True) for dir in dir_list))

            file_list = list(map(lambda node: node.abs_name, filter(
                lambda node: node.type is DirNodeType.File, tree)))

            for file in file_list:
                fw.write(file + "\n")

            # coord = Coordinatior(file_list)
            # await coord.start()

        await run_command(["mega-logout"])


if __name__ == "__main__":
    asyncio.run(main())
