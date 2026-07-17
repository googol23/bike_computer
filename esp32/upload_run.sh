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

  new_hash=$(
    find "$dir" \
      -type d -name "__pycache__" -prune -o \
      -type f -print \
    | xargs sha256sum \
    | sha256sum \
    | awk '{print $1}'
  )

  old_hash=$(grep "^$dir " "$state_file" | awk '{print $2}')

  if [ "$new_hash" != "$old_hash" ]; then
    echo "Uploading directory $dir"
    mpremote connect "$device" fs cp -r "$dir" :

    grep -v "^$dir " "$state_file" > "$state_file.tmp"
    echo "$dir $new_hash" >> "$state_file.tmp"
    mv "$state_file.tmp" "$state_file"
  fi
}

# External libs
upload mem.py


# Controlers and drivers
upload st7796.py
upload st7796_psram.py
upload bq25185.py
upload xpt2046.py
upload dev_controler/htu21/htu21.py

# Configuration
upload config.py
upload settings.py

# Fonts
upload arial16.py
upload arial24.py
upload arial30.py
upload arial48.py


# Data
upload_dir routes
upload_dir nav_icons

# Main app
upload main.py
upload app.py

# Custom libs
# Navigation
upload_dir gpx
upload gnss.py
# Interface
upload hud.py
upload touch_handler.py
upload events.py

upload_dir widgets


upload led_status_manager.py
upload ble_gps_server.py
upload alarms.py
upload route.py
upload timer.py


mpremote connect "$device" reset
sleep 1
picocom -b 115200 "$device"