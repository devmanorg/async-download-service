from aiohttp import web
import aiofiles
import asyncio
import logging
import os

INTERVAL_SECS = 1
CHUNK_SIZE = 100000

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def archive(request):
    archive_hash = request.match_info.get("archive_hash", "Anonymous")
    cwd = os.getcwd()
    archive_path = f"{cwd}/test_photos/{archive_hash}/"
    if not os.path.exists(archive_path):
        raise web.HTTPNotFound()
    response = web.StreamResponse()
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers["Content-Disposition"] = "attachment; filename=photos.zip"
    await response.prepare(request)

    proc = await asyncio.create_subprocess_exec(
        "zip",
        "-r",
        "-",
        f".",
        "*",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=archive_path,
    )
    chunk_number = 0
    while True:
        logger.info(f"Sending archive chunk {chunk_number}")
        await asyncio.sleep(1)
        try:
            await response.write(await proc.stdout.read(n=CHUNK_SIZE))
        except ConnectionResetError:
            logger.error(f"Connection Break")
            break
        chunk_number += 1
        if proc.stdout.at_eof():
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
