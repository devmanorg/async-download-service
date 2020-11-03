import asyncio
from aiohttp import web
import aiofiles
import logging
import os
import argparse
from config import *


logger = logging.getLogger(__file__)


async def stop_archivate(proc):
    logging.info('скачивание остановлено пользователем')
    pid = proc.pid
    proc.kill()
    await proc.communicate()
    logging.info(f'process {pid} was killed')


async def archivate(request):
    response = web.StreamResponse()

    if os.path.exists(arg_config[PHOTOS_DIR]):
        photo_dir_path = arg_config[PHOTOS_DIR]
        dir_name_requested = os.path.split(photo_dir_path)[-1]
    else:
        dir_name_requested = request.match_info.get('archive_hash', EMPTY_ARCHIVE_NAME)
        photo_dir_path = f'./photos/{dir_name_requested}'

        dir_list = [dir_name for dir_name in os.listdir(PHOTOS_PATH) if os.path.isdir(os.path.join(PHOTOS_PATH, dir_name))]

    if dir_name_requested == EMPTY_ARCHIVE_NAME or dir_name_requested not in dir_list \
            or not os.path.exists(photo_dir_path):
        raise web.HTTPNotFound(text="Запрашиваемый архив не существует или удален")

    response.headers['Content-Type'] = f'attachment; filename="{dir_name_requested}.zip"'
    await response.prepare(request)

    proc = await asyncio.create_subprocess_exec('zip', '-', photo_dir_path,
                                                '-r',
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)

    try:
        while True:
            chunk = await proc.stdout.read(10000)
            if not chunk:
                break
            logging.info('Sending archive chunk...')

            await response.write(chunk)

            if arg_config[DELAY_RESPONSE]:
                await asyncio.sleep(arg_config[DELAY_RESPONSE])

    except asyncio.CancelledError:
        raise
    except Exception:
        raise
    except SystemExit:
        raise
    finally:
        await stop_archivate(proc)

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Async download file service')
    parser.add_argument('--logging', type=bool, default=False, help='Logging enable/disable')
    parser.add_argument('--resp_delay', type=int, default=0, help='Response delay in sec', dest='delay')
    parser.add_argument('--photo_dir', type=str, default='', help='Photo directory path')
    args = parser.parse_args()

    arg_config[DELAY_RESPONSE] = args.delay
    arg_config[PHOTOS_DIR] = args.photo_dir

    print('arg_config =', arg_config)

    if os.path.exists(args.photo_dir):
        PHOTOS_PATH = args.photo_dir
    else:
        PHOTOS_PATH = os.path.join(os.getcwd(), PHOTOS_DIR)

    if args.logging:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app, port=8080)

