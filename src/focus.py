import io
import logging
import time
import asyncio
import json

from aiohttp import web
import numpy as np
from scipy import ndimage

from .templates import html_response


logger = logging.getLogger("focus")
logger.setLevel(logging.DEBUG)


SAMPLE_FREQUENCY = 10  # Hertz
MAXXING_WINDOW = 10  # seconds
AVERAGING_WINDOW = 10  # seconds


convert_to_gray = lambda rgb : np.dot(rgb[... , :3] , [0.299 , 0.587, 0.114])


async def focus_page_handler(request):
    return html_response('./src/templates/focus.html')


async def get_laplacian_variance(camera):
    while True:
        image = camera.capture_array()
        image_gray = convert_to_gray(image)
        laplacian = ndimage.laplace(image_gray).var()
        yield laplacian
        await asyncio.sleep(1/SAMPLE_FREQUENCY)


async def focus_stream_handler(request):
    logging.info("📡 Client connected to focus")

    camera = request.app["camera"]
    capture_config = camera.create_preview_configuration()
    camera.switch_mode(capture_config)

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'

    await response.prepare(request)

    laplacian = get_laplacian_variance(camera)

    lvar = [await anext(laplacian)] * (MAXXING_WINDOW * SAMPLE_FREQUENCY)
    
    try:
        while True:
            lvar.append(await anext(laplacian))
            lvar.pop(0)
            json_str = json.dumps(
                {
                    "lvar": lvar[-1],
                    "lvar_max": max(lvar)
                }
            )
            await response.write(f'data:{json_str}\n\n'.encode())
            await asyncio.sleep(1/SAMPLE_FREQUENCY)
             
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            logger.warning("⚠️ Client disconnected.")
    except Exception as e:
        logger.error(f"❌ Unknown streaming error: {e}")
    finally:
        try:
            await response.write_eof()
        except:
            pass
        logger.info("🔁 Stream ended.")
        return response
