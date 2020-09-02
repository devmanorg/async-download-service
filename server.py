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


async def get_zip_pid(ps_stdout):
    zip_pid = 0
    running_process_list = ps_stdout.decode().splitlines()
    print(running_process_list)
    for process_line in running_process_list:
        process_list = process_line.split()
        if process_list[-1] == 'zip':
            zip_pid = process_list[0]
    return zip_pid


async def kill_process_on_pid(pid):
    proc = await asyncio.create_subprocess_shell(f'kill {pid}',
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)
    await proc.communicate()
    print(f'process {pid} was killed')


async def terminate_zip_process():
    proc = await asyncio.create_subprocess_exec('ps',
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    zip_pid = await get_zip_pid(stdout)
    await kill_process_on_pid(zip_pid)


async def show_zip_pid():
    while True:
        proc = await asyncio.create_subprocess_exec('ps',
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        zip_pid = await get_zip_pid(stdout)

        print(zip_pid)
        await asyncio.sleep(2)


async def archivate(request):
    response = web.StreamResponse()
    dir_name_requested = request.match_info.get('archive_hash', EMPTY_ARCHIVE_NAME)
    dir_list = [dir_name for dir_name in os.listdir(PHOTOS_PATH) if os.path.isdir(os.path.join(PHOTOS_PATH, dir_name))]
    if dir_name_requested == EMPTY_ARCHIVE_NAME or dir_name_requested not in dir_list:
        raise web.HTTPNotFound(text="Запрашиваемый архив не существует или удален")

    response.headers['Content-Type'] = f'attachment; filename="{dir_name_requested}.zip"'
    await response.prepare(request)

    cmd = f"cd test_photos;zip - {dir_name_requested} -r"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    size = 0
    try:
        while True:
            chunk = await proc.stdout.read(10000)
            if not chunk:
                break
            logging.info('Sending archive chunk...')
            await response.write(chunk)
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print('скачивание остановлено пользователем')
        await terminate_zip_process()

    await show_zip_pid()

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
