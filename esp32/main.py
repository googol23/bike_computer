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

from machine import Pin, I2C

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

    # --- Display init ---
    display = ST7796DisplayPSRAM(TFT_WIDTH, TFT_HEIGHT)
    display.clear(0xFFFFFF)
    display.set_backlight(50)
    # display = SimulatedDisplay(TFT_WIDTH, TFT_HEIGHT, "render_debug")

    # --- Touch screen init ---
    touch = XPT2046(
        sck_pin = config.TOUCH_PIN_CLK,
        mosi_pin = config.TOUCH_PIN_DIN,
        miso_pin = config.TOUCH_PIN_DO,
        cs_pin = config.TOUCH_PIN_CS,
        irq_pin = config.TOUCH_PIN_IRQ,
        width = TFT_WIDTH,
        height = TFT_HEIGHT,
        spi_id = 2,
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
