import asyncio
import sys

from aiohttp import web
import aiofiles
import logging
import os
import argparse
import const


logger = logging.getLogger(__file__)


def err_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


async def stop_archivate(proc):
    logging.info('скачивание остановлено пользователем')
    pid = proc.pid
    proc.kill()
    await proc.communicate()
    logging.info(f'process {pid} was killed')


async def archivate(request):
    response = web.StreamResponse()

    photo_dir_path = app[const.PHOTOS_DIR]

    try:
        dir_name_requested = request.match_info.get('archive_hash')
    except TypeError:
        raise web.HTTPNotFound(text="Отсутствует запрос")

    photo_dir_path = os.path.join(photo_dir_path, dir_name_requested)

    if not os.path.exists(photo_dir_path):
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

            if app[const.RESPONSE_DELAY]:
                await asyncio.sleep(app[const.RESPONSE_DELAY])
    finally:
        await stop_archivate(proc)

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
    
    parser = argparse.ArgumentParser(description='Async download file service')
    parser.add_argument('--logging_disable', default=True, help='Logging disable',
                        action='store_false', dest='logging')
    parser.add_argument('--resp_delay', type=int, default=0, help='Response delay in sec', dest='delay')
    parser.add_argument('--photo_dir', type=str, default='', help='Photo directory path')
    args = parser.parse_args()

    app[const.RESPONSE_DELAY] = args.delay
    app[const.PHOTOS_DIR] = args.photo_dir

    if args.logging:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    if os.path.exists(args.photo_dir):
        PHOTOS_PATH = args.photo_dir
    else:
        err_print("Несуществующий каталог файлов")
        logger.error("Задана не существующая папка")
        sys.exit()

    web.run_app(app, port=8080)

