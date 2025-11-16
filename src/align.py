import io
import logging
import time
import asyncio

from PIL import Image
from aiohttp import web
import aiohttp_jinja2

from .templates import html_response


REFERENCE_IMAGE_FIL = "referemce.jpg"


logger = logging.getLogger("stream")
logger.setLevel(logging.DEBUG)


params = {
    "opacity": 0.5
}


@aiohttp_jinja2.template("align.html")
async def align_page_handler(request):
    return {"page_title": "Alignment Tool"}


async def align_stream_handler(request):
    logger.info("📡 Client connected to alignment stream")

    camera = request.app["camera"]
    capture_config = camera.create_preview_configuration()
    camera.switch_mode(capture_config)

    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'multipart/x-mixed-replace; boundary=frame'
        }
    )

    await response.prepare(request)

    i = 0
    try:
        while True:
            reference = 'reference.jpg'
            ref = Image.open(reference)
            ref = ref.convert("RGB")

            frame = camera.capture_image().rotate(90, expand=True)
            frame = frame.convert("RGB")
            
            if i == 0:
                logger.debug(f"Loaded reference image - size: {ref.size}, mode: {ref.mode}, format: {ref.format}")
                logger.debug(f"Loaded reference image - size: {frame.size}, mode: {frame.mode}, format: {frame.format}")
                i += 1
            
            blend = Image.blend(ref, frame, params["opacity"])
            blend.convert('RGB')

            stream = io.BytesIO()
            blend.save(stream, format='JPEG')
            jpeg_bytes = stream.getvalue()

            await response.write(b"--frame\r\n")
            await response.write(b"Content-Type: image/jpeg\r\n")
            await response.write(f"Content-Length: {len(jpeg_bytes)}\r\n\r\n".encode())
            await response.write(jpeg_bytes)
            await response.write(b"\r\n")
            await asyncio.sleep(0.01)

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


async def reference_adjust_handler(request):
    data = await request.json()

    response = web.StreamResponse(
            status=200,
            reason='OK'
        )
    
    await response.prepare(request)

    params["opacity"] = int(data["opacity"]) / 100
    
    return response
    


async def reference_capture_handler(request):
    logger.info("📡 Client sent request to capture alignment reference")

    response = web.StreamResponse(
        status=200,
        reason='OK'
    )

    await response.prepare(request)

    camera = request.app['camera']

    ref = camera.capture_image("main").rotate(90, expand=True)
    ref.convert("RGB")
    ref.save('reference.jpg', 'JPEG', quality=95)

    return response
