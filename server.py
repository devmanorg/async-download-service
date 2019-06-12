import asyncio
import os
import sys
import signal
from aiohttp import web
from functools import partial
import aiofiles
import subprocess
import logging
import argparse


def make_command(compression_ratio, path):
    _compression = '-9'
    if compression_ratio in range(0, 10):
        _compression = f'-{compression_ratio}'
    logging.debug(f'compression ratio={_compression}')
    return 'zip', '-r', _compression, '-', path


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


async def make_zip_archive(request, delay, compression_ratio,
                           folder_with_photos):
    chunk_size = 1048576
    archive_hash = request.match_info.get('archive_hash')
    archive_path = os.path.join(folder_with_photos, archive_hash)

    if not os.path.exists(archive_path):
        _reason = 'No archive in {} !'.format(folder_with_photos)
        raise web.HTTPNotFound(reason=_reason)

    cmd = make_command(compression_ratio, path=archive_path)
    zip_process = await asyncio.create_subprocess_exec(*cmd,
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
    logging.debug('Process PID={}'.format(zip_process.pid))

    response = web.StreamResponse()
    _headers = 'attachment; filename={}.zip'.format(archive_hash)
    response.headers['Content-Disposition'] = _headers
    await response.prepare(request)

    try:
        counter = 0
        while True:
            _chunk = await zip_process.stdout.read(chunk_size)
            counter += 1
            logging.debug('Download chunk {}'.format(counter))
            await response.write(_chunk)
            await asyncio.sleep(delay)

            if not _chunk:
                break

    except (ConnectionResetError, asyncio.CancelledError):
        logging.debug('Download was interrupted')
        raise
    finally:
        try:
            os.kill(zip_process.pid, signal.SIGKILL)
        except OSError:
            pass
        response.force_close()
        logging.debug('Download finished')

    return response


def get_args_parser():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=formatter_class)
    parser.add_argument('-f', '--folder', type=str,
                        default='test_photos', help='set photos folder')
    parser.add_argument('-c', '--compression', type=int, default=9,
                        help='set compression ratio - min=0, max=9')
    parser.add_argument('-d', '--delay', type=int, default=1,
                        help='set delay of download chunk - min=0, max=9')
    parser.add_argument('-l', '--logs', action='store_true', default=False,
                        help='set logging')
    return parser


def main():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.split(dir_path)[0])
    parser = get_args_parser()
    args = parser.parse_args()
    if args.logs:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug('DEBUG mode')

    delay = 1
    if args.delay in range(0, 10):
        delay = args.delay

    archivator = partial(make_zip_archive, delay=delay,
                         compression_ratio=args.compression,
                         folder_with_photos=args.folder)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivator)
    ])
    web.run_app(app, port=8080)


if __name__ == '__main__':
    main()
