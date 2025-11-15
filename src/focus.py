import io
import logging
import time
import asyncio
import json

from aiohttp import web
import numpy as np
from scipy import ndimage
import aiohttp_jinja2

from .templates import html_response


logger = logging.getLogger("focus")
logger.setLevel(logging.DEBUG)


SAMPLE_FREQUENCY = 10  # Hertz (only notional)
AVERAGING_WINDOW = 5  # samples
MAXXING_WINDOW = 6  # batchs of averaging samples


convert_to_gray = lambda rgb : np.dot(rgb[... , :3] , [0.299 , 0.587, 0.114])


@aiohttp_jinja2.template("focus.html")
async def focus_page_handler(request):
    return {"page_title": "Focus Tool"}


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

    start_var = await anext(laplacian)
    
    lvar_samples = [start_var] * AVERAGING_WINDOW
    lvar_mvg_avgs = [start_var] * MAXXING_WINDOW
    lvar_max = start_var
    
    try:
        while True:
            lvar_sample = await anext(laplacian)
            lvar_samples.append(lvar_sample)
            lvar_samples.pop(0)
            
            mvg_avg = np.mean(lvar_samples[-AVERAGING_WINDOW:])
            lvar_mvg_avgs.append(mvg_avg)
            lvar_mvg_avgs.pop(0)
            
            lvar_max = max(lvar_mvg_avgs)
            
            json_str = json.dumps(
                {
                    "lvar": mvg_avg,
                    "lvar_max": lvar_max
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
