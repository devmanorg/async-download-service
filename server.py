import asyncio
import logging
import os
import subprocess

import aiofiles
from aiohttp import web


logging.basicConfig(
    format=(
        '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
        '%(message)s'
    ),
    level=logging.DEBUG
)


async def archive(request):
    archive_hash = request.match_info.get('archive_hash')

    if not os.path.isdir(f'./test_photos/{archive_hash}'):
        raise web.HTTPNotFound(text='404 - страница не найдена')

    cmd = ['zip', '-r', '-j', '-', f'./test_photos/{str(archive_hash)}']
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    response = web.StreamResponse()

    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = (
        f'attachment; filename="{archive_hash}.zip"'
    )

    await response.prepare(request)

    chunk_number = 1
    try:
        while not process.stdout.at_eof():
            stdout = await process.stdout.read(sample_size)
            logging.info(f'Sending archive chunk {chunk_number} ...')
            chunk_number += 1
            await response.write(stdout)
            await asyncio.sleep(10)

    except asyncio.CancelledError:
        logging.warning(f'Download was interrupted')  
    finally:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    sample_size = 1024 * 100
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
