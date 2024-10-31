import asyncio
import typing


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
            print(f"Error running {' '.join(command)}: {stderr.decode()}")

        return stdout.decode()
    except Exception as e:
        print(f"Exception while running {' '.join(command)}: {e}")
        return None


def get_path_without_root(path: str) -> str:
    return path[path.index('/') + 1:]
