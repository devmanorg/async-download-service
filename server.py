import asyncio
from aiohttp import web
import aiofiles
import logging
import os

INTERVAL_SECS = 1
PHOTOS_DIR = 'test_photos'
PHOTOS_PATH = os.path.join(os.getcwd(), PHOTOS_DIR)
EMPTY_ARCHIVE_NAME = "empty_archive_name"

logging.basicConfig(level=logging.INFO)


async def kill_process_on_pid(pid):
    proc = await asyncio.create_subprocess_exec('kill', '-9', str(pid),
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)
    await proc.communicate()
    logging.info(f'process {pid} was killed')


async def stop_archivate(proc):
    logging.info('скачивание остановлено пользователем')
    # await terminate_zip_process()
    await kill_process_on_pid(proc.pid)
    await proc.communicate()


async def archivate(request):
    response = web.StreamResponse()
    dir_name_requested = request.match_info.get('archive_hash', EMPTY_ARCHIVE_NAME)
    dir_list = [dir_name for dir_name in os.listdir(PHOTOS_PATH) if os.path.isdir(os.path.join(PHOTOS_PATH, dir_name))]
    if dir_name_requested == EMPTY_ARCHIVE_NAME or dir_name_requested not in dir_list:
        raise web.HTTPNotFound(text="Запрашиваемый архив не существует или удален")

    response.headers['Content-Type'] = f'attachment; filename="{dir_name_requested}.zip"'
    await response.prepare(request)

    proc = await asyncio.create_subprocess_exec('zip', '-', f'./test_photos/{dir_name_requested}',
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
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        await stop_archivate(proc)
    except Exception:
        await stop_archivate(proc)
    except SystemExit:
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
    web.run_app(app, port=8081)
