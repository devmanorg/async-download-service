from aiohttp import web
import aiofiles
import argparse
import asyncio
import logging
import os

INTERVAL_SECS = 0
CHUNK_SIZE = 100000


parser = argparse.ArgumentParser(description="AioHTTP Photos Archive Server")
parser.add_argument(
    "--logging", action="store_true", dest="logging_enabled", help="Enable logging"
)
parser.add_argument(
    "--delay", dest="response_delay", type=int, help="Response delay in seconds"
)
parser.add_argument(
    "--photos-dir",
    dest="photos_directory",
    type=str,
    help="Path to the directory with photos",
)
args = parser.parse_args()

logging_enabled = (
    args.logging_enabled
    if args.logging_enabled is not None
    else os.getenv("LOGGING_ENABLED", "true").lower() == "true"
)
response_delay = (
    args.response_delay
    if args.response_delay is not None
    else int(os.getenv("RESPONSE_DELAY", INTERVAL_SECS))
)
photos_directory = (
    args.photos_directory
    if args.photos_directory is not None
    else os.getenv("PHOTOS_DIRECTORY", None)
)

if logging_enabled:
    logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ArchiveHandler:
    def __init__(self, archive_path):
        self.proc = None
        self.archive_path = archive_path

    async def start_archive_process(self):
        self.proc = await asyncio.create_subprocess_exec(
            "zip",
            "-r",
            "-",
            f".",
            "*",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.archive_path,
        )

    async def stop_archive_process(self):
        if self.proc:
            self.proc.terminate()
            await self.proc.communicate()


async def archive(request):
    archive_hash = request.match_info.get("archive_hash", "Anonymous")
    cwd = os.getcwd()
    archive_path = (
        f"{cwd}/test_photos/{archive_hash}/"
        if not photos_directory
        else photos_directory
    )
    if not os.path.exists(archive_path):
        raise web.HTTPNotFound()
    response = web.StreamResponse()
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers["Content-Disposition"] = "attachment; filename=photos.zip"
    await response.prepare(request)

    archive_handler = ArchiveHandler(archive_path=archive_path)
    await archive_handler.start_archive_process()

    chunk_number = 0
    while True:
        logger.info(f"Sending archive chunk {chunk_number}")
        if response_delay:
            await asyncio.sleep(response_delay)
        try:
            await response.write(await archive_handler.proc.stdout.read(n=CHUNK_SIZE))
        except ConnectionResetError:
            logger.error(f"Download was interrupted, terminating zip process")
            await archive_handler.stop_archive_process()
            break
        except Exception:
            logger.error(f"Exception, terminating zip process")
            await archive_handler.stop_archive_process()
            break
        chunk_number += 1
        if archive_handler.proc.stdout.at_eof():
            logger.info(f"Complete")
            break
    return response


async def handle_index_page(request):
    async with aiofiles.open("index.html", mode="r") as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type="text/html")


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_index_page),
            web.get("/archive/{archive_hash}/", archive),
        ]
    )
    web.run_app(app)
