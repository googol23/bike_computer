# device=/dev/ttyUSB0
device=/dev/ttyACM0
# cp gpx_streamer.py /mnt/c/Users/googo/Documents/gpx_simulator/.
mpremote connect $device fs cp config.py :
mpremote connect $device fs cp led_status_manager.py :
mpremote connect $device fs cp bq25185.py :

mpremote connect $device fs cp mem.py :
mpremote connect $device fs cp timer.py :
mpremote connect $device fs cp app.py :

mpremote connect $device fs cp hud.py :
mpremote connect $device fs cp widget.py :

mpremote connect $device fs cp ble_gps_server.py :
mpremote connect $device fs cp route.py :
mpremote connect $device fs cp gpx_streamer.py :

mpremote connect $device fs cp -r routes/ :

mpremote connect $device fs cp sdcard/* :


mpremote connect $device fs cp st7796.py :

mpremote connect $device fs cp writer.py :
mpremote connect $device fs cp arial30.py :

mpremote connect $device fs cp main.py :

mpremote connect $device reset

sleep 1

picocom -b 115200 $device