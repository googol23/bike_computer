# Bike Computer

A custom **ESP32-S3 bike computer** built with MicroPython. It provides a touchscreen ride dashboard, GPX-based navigation, GNSS integration, ride statistics, sensor support, and battery/charging status handling.

## Features

- Live speed, average speed, distance, and ride timer
- GPX route loading and turn-by-turn navigation display
- ST7796 touchscreen display with XPT2046 touch controller
- GNSS support through UBX `NAV-PVT` messages
- Temperature and humidity sensor support
- Alarm/reminder system
- BQ25185 battery charger status support
- Desktop tools for downloading and preparing route data

## Hardware

The current configuration targets an **ESP32-S3 N16R8** board with:

- ST7796 display
- XPT2046 touch controller
- GNSS module
- BQ25185 charging module
- HTU21 temperature/humidity sensor
- SD card interface

Pin assignments are defined in `esp32/config.py`.

## Project Structure

```text
esp32/       MicroPython firmware, drivers, UI, navigation, and route files
route_gen/   Desktop scripts for generating and downloading routes
```

## Setup

1. Install MicroPython tools:

   ```bash
   pip install mpremote
   ```

2. Flash the included ESP32-S3 MicroPython firmware if required.

3. Review the hardware pins in:

   ```text
   esp32/config.py
   ```

4. Connect the board and upload the firmware files:

   ```bash
   cd esp32
   chmod +x upload_run.sh
   ./upload_run.sh
   ```

The upload script currently expects the device at `/dev/ttyACM0`.

## Route Tools

The scripts in `route_gen/` use services such as GraphHopper, OpenRouteService, and OpenStreetMap data. Install their Python dependencies as needed and provide API keys through local configuration or environment variables.

Generated GPX routes should be placed in `esp32/routes/`.

## Status

This project is under active development. Some runtime tasks and hardware features may need to be enabled or adjusted in `esp32/app.py` for the target device.

## License

Licensed under the **PolyForm Noncommercial License 1.0.0**. See `LICENSE` for details.
