import os
import asyncio
import uvloop
import logging
import aiofiles

from coordinator import Coordinatior
from utils import run_command
from mega_parser import DirNodeType, MegaParserSettings, MegaResultParser

folder_url = 'https://mega.nz/folder/0Sg0iD4B#0OPF1JJgFjtYoJuStlsCtA'

logger = logging.getLogger(__name__)


async def main():
    logger.debug("logging in")
    await run_command(["mega-cmd"], f"login {folder_url}")

    logger.debug("creating data dir")
    if not os.path.exists('data'):
        os.mkdir('data')

    if not os.path.exists('data/dir_names.txt'):
        logger.debug("running mega-ls")
        stdout = await run_command(["mega-ls", "-r"])
        folders = stdout.splitlines()

        logger.debug("creating data/dir_names.txt")
        async with aiofiles.open("data/dir_names.txt", "w") as fw:
            await fw.writelines(f + '\n' for f in folders)

    if not os.path.exists('data/files.txt'):
        logger.debug("creating data/files.txt")
        async with aiofiles.open("data/files.txt", "w") as fw, aiofiles.open("data/dir_names.txt", "r") as dn_file:
            text = await dn_file.read()
            parser = MegaResultParser(
                "data/CS",
                text,
                MegaParserSettings([".txt", ".pdf", ".doc"], ["20229 - אלגברה לינארית 2/Mamans/2009a"]))

            logger.debug("parsing dir tree")
            tree = parser.parse()

            dir_list = list(map(lambda node: node.abs_name, filter(
                lambda node: node.type is DirNodeType.Dir, tree)))

            await asyncio.gather(*(asyncio.to_thread(os.makedirs, dir, exist_ok=True) for dir in dir_list))

            file_list = list(map(lambda node: node.abs_name, filter(
                lambda node: node.type is DirNodeType.File, tree)))

            await fw.writelines(f + '\n' for f in file_list)

            coord = Coordinatior(file_list)
            await coord.start()

        await run_command(["mega-logout"])

if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
