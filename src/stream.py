from PIL import Image
from aiohttp import web
import io
import logging
import time
import asyncio

from .templates import html_response

logger = logging.getLogger("stream")


async def feed_page_handler(request):
    return html_response('./src/templates/feed.html')


async def feed_stream_handler(request):
    logger.info("📡 Client connected to stream")

    camera = request.app['camera']
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

    try:
        while True:
            frame = camera.capture_array("main")

            stream = io.BytesIO()
            Image.fromarray(frame).rotate(90, expand=True).convert("RGB").save(stream, format='JPEG')
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
