import argparse
import asyncio
import logging
import os
import signal
import subprocess

import aiofiles
from aiohttp import web

logger = logging.getLogger('server')
SAMPLE_SIZE = 1024 * 100


async def archive(request):
    
    archive_hash = request.match_info['archive_hash']
    if not os.path.isdir(f'{photos_dir}{archive_hash}'):
        raise web.HTTPNotFound(text='404 - страница не найдена')

    cmd = ['zip', '-r', '-', f'{photos_dir}{str(archive_hash)}']
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
            stdout = await process.stdout.read(SAMPLE_SIZE)
            logging.info(f'Sending archive chunk {chunk_number} ...')
            chunk_number += 1
            await response.write(stdout)
            if delay_enabled:
                await asyncio.sleep(10)

    except asyncio.CancelledError as cancelled_error:
        logging.warning('Download was interrupted')
        raise cancelled_error
    except KeyboardInterrupt:
        try:
            process.communicate()
            process.send_signal(signal.SIGTERM)
        except AttributeError:
            logging.warning('There was no process')
    finally:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        except AttributeError:
            logging.warning('There was no process')

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', help='Enable Logging')
    parser.add_argument('--delay', help=('Make download sleep for 10 seconds '
                                         'every chunk of data'))
    parser.add_argument('--photos', help='Root folder for photo directories')
    args = parser.parse_args()

    delay_enabled = args.delay
    logging_enabled = args.logging
    photos_dir = args.photos if args.photos else './test_photos/'

    if not logging_enabled:
        logger.disabled = True
    else:
        logging.basicConfig(
            format=(
                '%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s] '
                '%(message)s'
            ),
            level=logging.INFO
        )

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
