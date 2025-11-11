import datetime
import logging
import asyncio
from dateutil import tz as tz_handler

import schedule
from suntime import Sun
from picamera2 import Picamera2


LAT, LONG = 40.730610, -73.935242
tz_local = "US/Eastern"

logger = logging.getLogger("capture")
logger.setLevel(logging.INFO)


async def run_capture_loop(camera):
    schedule.every().day.at("00:00", tz_local).do(schedule_day, camera=camera)
    schedule_day(camera)
    logger.info("Time lapse capture loop started.")
    
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)


def schedule_day(camera):
    schedule.cancel_job(snap_hd)
    for t in get_times():
        schedule.every(1).day.at(t, tz_local).do(snap_hd, camera=camera)
        logger.debug(f"Image capture scheduled for {t}")
    logger.debug(f"Schedule set for {datetime.date.today()}")



def get_times():
    sun = Sun(LAT, LONG)
    sr = sun.get_sunrise_time(time_zone=tz_handler.gettz(tz_local))
    ss = sun.get_sunset_time(time_zone=tz_handler.gettz(tz_local))
    yield sr.strftime("%H:%M")
    for h in range(sr.hour+1, ss.hour+1):
        yield datetime.time(h).strftime("%H:%M")
    yield ss.strftime("%H:%M")


def snap_hd(camera: Picamera2):
    config = camera.create_still_configuration()
    camera.switch_mode_and_capture_file(
        config, 
        f"./images/{datetime.datetime.now()}.jpg".replace(":","-")
        )
    logger.debug(f"Photo taken at {datetime.datetime.now()}")
