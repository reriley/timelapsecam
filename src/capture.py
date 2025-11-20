import datetime
import logging
import asyncio
from dateutil import tz as tz_handler

import schedule
from suntime import Sun
from picamera2 import Picamera2


LAT, LONG = 40.730610, -73.935242
TZ_LOCAL = "US/Eastern"
IMAGE_DIR ="./images"

logger = logging.getLogger("capture")
logger.setLevel(logging.INFO)

persistent_schedule = schedule.Scheduler()
daily_schedule = schedule.Scheduler()


async def run_capture_loop(camera):
    persistent_schedule.every().day.at("00:00", TZ_LOCAL).do(schedule_day, camera=camera)
    schedule_day(camera)
    logger.info("Time lapse capture loop started.")
    
    while True:
        persistent_schedule.run_pending()
        daily_schedule.run_pending()
        await asyncio.sleep(60)


def schedule_day(camera):
    daily_schedule.clear()
    for t in get_times():
        daily_schedule.every(1).day.at(t, TZ_LOCAL).do(snap_hd, camera=camera)
        logger.debug(f"Image capture scheduled for {t}")
    logger.debug(f"Schedule set for {datetime.date.today()}")


def get_times():
    sun = Sun(LAT, LONG)
    sr = sun.get_sunrise_time(time_zone=tz_handler.gettz(TZ_LOCAL))
    ss = sun.get_sunset_time(time_zone=tz_handler.gettz(TZ_LOCAL))
    yield sr.strftime("%H:%M")
    for h in range(sr.hour+1, ss.hour+1):
        yield datetime.time(h).strftime("%H:%M")
    yield ss.strftime("%H:%M")


def snap_hd(camera: Picamera2):
    config = camera.create_still_configuration()
    camera.switch_mode_and_capture_file(
        config, 
        f"{IMAGE_DIR}/{datetime.datetime.now()}.jpg".replace(":","-")
        )
    logger.debug(f"Photo taken at {datetime.datetime.now()}")
