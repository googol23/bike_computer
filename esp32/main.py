import config
import asyncio
from app import AppManager, TFT_HEIGHT, TFT_WIDTH


import bq25185
from st7796 import ST7796Display

from led_status_manager import LEDStatusManager, LEDState

# from machine import Pin, SPI
# import os
# import sdcard

# cs = Pin(config.SD_PIN_CS, Pin.OUT, value=1)
# spi = SPI(2, baudrate=400000, sck=Pin(config.SD_PIN_SCK), mosi=Pin(config.SD_PIN_MOSI), miso=Pin(config.SD_PIN_MISO))
# sd = sdcard.SDCard(spi, cs)

# os.mount(sd, "/sd")

# # Write file
# with open("/sd/test.txt", "w") as f:
#     f.write("Hello ESP32 SD card")

# # Read file
# with open("/sd/test.txt", "r") as f:
#     print(f.read())

# print(os.listdir("/sd"))


async def main():

    # --- LED starts immediately ---
    led = LEDStatusManager(pin=48)
    led.start()
    led.set_state(LEDState.BOOT)

    # --- Charger init ---
    charger = bq25185.BQ25185(
        stat_1_pin=config.CHARGE_PIN_STAT1,
        stat_2_pin=config.CHARGE_PIN_STAT2
    )

    led.set_state(LEDState.INIT)

    # --- Display init ---
    display = ST7796Display(TFT_WIDTH, TFT_HEIGHT)
    display.clear(0xFFFFFF)
    display.set_backlight(50)

    led.set_state(LEDState.READY)

    # --- App manager ---
    app_man = AppManager(display=display, charger=charger)

    try:
        await app_man.run()
    except Exception as e:
        led.set_state(LEDState.ERROR)
        raise e


asyncio.run(main())
