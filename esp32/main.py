import asyncio
from app import AppManager, TFT_HEIGHT, TFT_WIDTH

import bq25185
from st7796 import ST7796Display


print("Booting...")
charger = bq25185.BQ25185(stat_1_pin=25, stat_2_pin=26)

display = ST7796Display(TFT_WIDTH, TFT_HEIGHT)
display.clear()
display.show_logo("logo.rgb565")


app_man = AppManager(display=display, charger=charger)

asyncio.run(app_man.run())