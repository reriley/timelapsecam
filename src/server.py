import logging
import asyncio

from aiohttp import web


PORT = 8080


logger = logging.getLogger("server")


async def start_server(runner):
    logger.info(f"🟠 Starting web server on port {PORT}...")
    
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=PORT)
    await site.start()
    logger.info(f"🟢 Web server running.")
    await asyncio.Event().wait()


async def stop_server(runner):
    await runner.cleanup()
    logger.info(f"🔴 Web server stopped.")
