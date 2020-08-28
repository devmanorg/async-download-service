import asyncio
from aiohttp import web
import aiofiles
import os

INTERVAL_SECS = 1
EMPTY_ARCHIVE_NAME = "empty_archive_name"


async def archivate(request):

    dir_name = request.match_info.get('archive_hash', "empty_archive_name")
    if dir_name == EMPTY_ARCHIVE_NAME:
        raise web.HTTPFound('')

    response = web.StreamResponse()

    response.headers['Content-Type'] = f'attachment; filename="{dir_name}.zip"'
    await response.prepare(request)

    cmd = f"cd test_photos;zip - {dir_name} -r"
    print(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    size = 0
    while True:
        chunk = await proc.stdout.read(50)
        if not chunk:
            print(size)
            break
        size += len(chunk)
        await response.write(chunk)

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
