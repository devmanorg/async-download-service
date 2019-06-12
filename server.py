import asyncio
import os
import sys
from aiohttp import web
import datetime
import logging
import aiofiles
import subprocess
import logging
import argparse
from dotenv import load_dotenv


INTERVAL_SECS = 1
FOLDER_WITH_PHOTOS = 'test_photos'
CHUNK_SIZE = 1048576


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


async def archivate(request):
    counter = 0
    archive_hash = request.match_info.get('archive_hash')
    archive_path = os.path.join(FOLDER_WITH_PHOTOS, archive_hash)
    logging.debug(archive_path)

    if not os.path.exists(archive_path):
        _reason = 'No find archive in {} !'.format(FOLDER_WITH_PHOTOS)
        raise web.HTTPNotFound(reason=_reason)

    cmd = ['zip', '-r', '-9', '-', archive_path]
    logging.info(cmd)
    zip_process = await asyncio.create_subprocess_exec(*cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    response = web.StreamResponse()

    _headers = 'attachment; filename={}.zip'.format(archive_hash)
    response.headers['Content-Disposition'] = _headers
    await response.prepare(request)

    try:
        while True:
            _chunk = await zip_process.stdout.read(CHUNK_SIZE)
            counter += 1
            logging.info('Activity chunk № {}'.format(counter))
            await response.write(_chunk)

            await asyncio.sleep(INTERVAL_SECS)

            if not _chunk:
                break

    except (ConnectionResetError, asyncio.CancelledError):
        logging.info('Zip activity cancelled')
        zip_process.terminate()
        raise

    finally:
        response.force_close()
        logging.info('Zip activity finished')

    return response


def main():
    logging.basicConfig(level=logging.INFO)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.split(dir_path)[0])
    #load_dotenv()

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app, port=8080)



if __name__ == '__main__':
    main()

