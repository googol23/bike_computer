# mpremote connect /dev/ttyUSB0 fs cp map_render.py :
# 
mpremote connect /dev/ttyUSB0 fs cp rgb565/esp32.rgb565 :

mpremote connect /dev/ttyUSB0 fs cp bq25185.py :

mpremote connect /dev/ttyUSB0 fs cp mem.py :
mpremote connect /dev/ttyUSB0 fs cp app.py :

mpremote connect /dev/ttyUSB0 fs cp hud.py :
mpremote connect /dev/ttyUSB0 fs cp widget.py :

mpremote connect /dev/ttyUSB0 fs cp ble_gps_server.py :

mpremote connect /dev/ttyUSB0 fs cp st7796.py :

mpremote connect /dev/ttyUSB0 fs cp writer.py :
mpremote connect /dev/ttyUSB0 fs cp arial30.py :

mpremote connect /dev/ttyUSB0 fs cp main.py :

mpremote connect /dev/ttyUSB0 reset

sleep 1

picocom -b 115200 /dev/ttyUSB0