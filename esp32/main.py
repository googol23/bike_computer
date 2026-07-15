import asyncio

import config
import bq25185
import htu21
import gnss
from app import TFT_HEIGHT, TFT_WIDTH, AppManager
from led_status_manager import LEDState, LEDStatusManager
# from st7796 import ST7796DisplayPSRAM
from st7796_psram import ST7796DisplayPSRAM

from xpt2046 import XPT2046
# from dummy_display import SimulatedDisplay

from machine import Pin, I2C, SPI

import time

async def main():

    # --- GNSS init ---
    gnss_module = gnss.GNSSModule(config.GNSS_PIN_TX, config.GNSS_PIN_RX)

    # --- Charger init ---
    charger = bq25185.BQ25185(
        stat_1_pin=config.CHARGE_PIN_STAT1, stat_2_pin=config.CHARGE_PIN_STAT2
    )

    # led.set_state(LEDState.INIT)

    sensor = htu21.HTU21(scl_pin=config.TEMP_SENSOR_SCL, sda_pin=config.TEMP_SENSOR_SDA)
    # sensor.reset()

    Pin(config.DISPLAY_PIN_CS, Pin.OUT, value=1)
    Pin(config.TOUCH_PIN_CS, Pin.OUT, value=1)
    Pin(config.SD_PIN_CS, Pin.OUT, value=1)
    
    # Shared SPI bus for Display, SDCard reader, display touch controls
    shared_spi = SPI(
        config.SPI_BUS_ID,
        baudrate = config.SPI_BAUDRATE,
        polarity = config.SPI_POLAROTY,
        phase = config.SPI_PHASE,
        sck = Pin(config.SPI_BUS_SCK),
        mosi = Pin(config.SPI_BUS_MOSI),
        miso = Pin(config.SPI_BUS_MISO),
    )
    
    # --- Display init ---
    display = ST7796DisplayPSRAM(TFT_WIDTH, TFT_HEIGHT, shared_spi)
    display.clear(0xFFFFFF)
    display.set_backlight(100)
    # display = SimulatedDisplay(TFT_WIDTH, TFT_HEIGHT, "render_debug")

    # --- Touch screen init ---
    touch = XPT2046(
        spi = shared_spi,
        width = TFT_WIDTH,
        height = TFT_HEIGHT,
        cs_pin = config.TOUCH_PIN_CS,
        irq_pin = config.TOUCH_PIN_IRQ,
        swap_xy = False,
        invert_x = False,
        invert_y = True
    )

    # led.set_state(LEDState.READY)
    
    # --- App manager ---
    app_man = AppManager(display=display, charger=charger, gnss_module=gnss_module, sensors=[sensor], touch_gui=touch)

    try:
        await app_man.run()
    except Exception as e:
        # led.set_state(LEDState.ERROR)
        raise e


asyncio.run(main())
