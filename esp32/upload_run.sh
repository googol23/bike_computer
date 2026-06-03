#!/bin/bash

device=/dev/ttyACM0
state_file=.mpremote_hashes

touch "$state_file"

hash_file () {
  sha256sum "$1" | awk '{print $1}'
}

upload () {
  file="$1"
  new_hash=$(hash_file "$file")
  old_hash=$(grep "^$file " "$state_file" | awk '{print $2}')

  if [ "$new_hash" != "$old_hash" ]; then
    echo "Uploading $file"
    mpremote connect "$device" fs cp "$file" :

    grep -v "^$file " "$state_file" > "$state_file.tmp"
    echo "$file $new_hash" >> "$state_file.tmp"
    mv "$state_file.tmp" "$state_file"
  fi
}

upload_dir () {
  dir="$1"

  new_hash=$(find "$dir" -type f -exec sha256sum {} \; | sha256sum | awk '{print $1}')
  old_hash=$(grep "^$dir " "$state_file" | awk '{print $2}')

  if [ "$new_hash" != "$old_hash" ]; then
    echo "Uploading directory $dir"
    mpremote connect "$device" fs cp -r "$dir" :

    grep -v "^$dir " "$state_file" > "$state_file.tmp"
    echo "$dir $new_hash" >> "$state_file.tmp"
    mv "$state_file.tmp" "$state_file"
  fi
}

upload_dir routes
upload_dir nav_icons

upload arial16.py
upload arial24.py
upload arial30.py
upload arial48.py

upload gnss.py

upload arrow_sprites.py

upload config.py
upload led_status_manager.py
upload bq25185.py
upload mem.py
upload timer.py
upload app.py
upload hud.py
upload widget.py
upload ble_gps_server.py
upload route.py
upload gpx_streamer.py
upload st7796.py
upload main.py
upload navigation.py

mpremote connect "$device" reset
sleep 1
picocom -b 115200 "$device"