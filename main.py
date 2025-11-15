#!/usr/bin/env -S uv run --script


import time
import datetime
from dateutil import tz
import logging
import asyncio
from asyncio.exceptions import CancelledError

from suntime import Sun
from aiohttp import web
from picamera2 import Picamera2
import aiohttp_jinja2
import jinja2

from src import (
    start_server, 
    stop_server, 
    run_capture_loop, 
    feed_page_handler,
    feed_stream_handler,
    focus_page_handler, 
    focus_stream_handler,
    align_page_handler,
    align_stream_handler,
    reference_capture_handler,
    reference_adjust_handler
    )


logger = logging.getLogger("main")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
    filename="log",
    filemode="w",
    encoding="utf-8"
    )


async def main():
    logger.debug("Setting up camera...")
    camera = Picamera2()
    camera.options["quality"] = 80
    camera.options["compress_level"] = 2
    camera.start()
    logger.info("Camera setup complete.")
    
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./src/static'))
    app["camera"] = camera
    app.router.add_get('/', feed_page_handler)
    app.router.add_get('/feed_stream', feed_stream_handler)
    app.router.add_get('/focus', focus_page_handler)
    app.router.add_get('/focus_stream', focus_stream_handler)
    app.router.add_get('/align', align_page_handler)
    app.router.add_get('/align_stream', align_stream_handler)
    app.router.add_post('/align_capture', reference_capture_handler)
    app.router.add_post('/align_adjust', reference_adjust_handler)
    app.add_routes([web.static('/static', "./src/static")])
    
    runner = web.AppRunner(app)

    asyncio.create_task(start_server(runner))
    asyncio.create_task(run_capture_loop(camera))
    
    
    logger.info("All services launched.")

    try:
        await asyncio.Future()
    except:
        logger.info("Interrupted. Cleaning up...")
    finally:
        logger.info("Script Terminated.")
        await stop_server(runner)
        


if __name__ == "__main__":
    asyncio.run(main())
