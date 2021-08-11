import logging
import argparse
import asyncio
import aiofiles
from functools import partial
from pathlib import Path
from aiohttp import web

BASE_TIME_INTERVAL = 1

parser = argparse.ArgumentParser(
    description='Async app that creates zip archives.',
)
parser.add_argument(
    '-l', 
    '--logging', 
    help='Turn on logging', 
    action='store_true',
)
parser.add_argument(
    '-t', 
    '--timelag', 
    help='Add response time lag', 
    action='store_true',
)
parser.add_argument(
    '-fd', 
    '--filesdir', 
    help='Dir to store photo',
    default='test_photos',
)
args = parser.parse_args()

if args.logging:
    logging.basicConfig(level=logging.DEBUG)


async def archivate(request, zip_dir='', timelag = False, interval = 0):
    """Асинхронный обработчик для создания и получения архива."""
    zip_hash = request.match_info.get('archive_hash')        
    zip_folder_path = Path.cwd() / zip_dir / zip_hash

    if not zip_folder_path.is_dir():
        return web.Response(
            status='404',
            text='Folder not found.',
        )

    procedure_stdout = asyncio.subprocess.PIPE
    zip_procedure = await asyncio.create_subprocess_exec(
        'zip',
        '-r', 
        '-', 
        zip_hash,
        stdout=procedure_stdout,
        cwd=zip_dir,
    )

    zip_reader = zip_procedure.stdout
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = f'attachment; filename*=utf-8\'\'{zip_hash}.zip'

    await response.prepare(request)

    try:
        chunk_index = 0

        # Отправка данных архива кусками
        while not zip_reader.at_eof():
            archive_data = await zip_reader.read(10000)
            logging.debug(f'Sending archive chunk {chunk_index}')
            await response.write(archive_data)

            if timelag:
                await asyncio.sleep(interval)

            chunk_index += 1
        
    finally:
        await asyncio.sleep(1)
        
        if zip_procedure.returncode is None:
            zip_procedure.kill()
            zip_procedure.communicate()
            
        logging.debug('Download was interrupted')
    
    return response


async def handle_index_page(request):
    """Обработчик главной страницы."""
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(
        text=index_contents, 
        content_type='text/html',
    )


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get(
            '/archive/{archive_hash}/', 
            partial(
                archivate,
                zip_dir=args.filesdir,
                timelag=args.timelag,
                interval=BASE_TIME_INTERVAL,
            ),
        ),
    ])
    web.run_app(app)
