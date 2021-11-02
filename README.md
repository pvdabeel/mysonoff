
# MySonoff - OS X Menubar plugin

Displays information about your Sonoff switches. Allows you to control the switches in your home via the Ewelink API.

![Imgur](https://i.imgur.com/e01uIu6.png)

**Update 2021.11.02:**
- [X] Added support for Xbar

**Update 2019.08.27:**
- [X] Added support for Sonoff devices with multiple outlets

**Update 2019.08.13:**
- [X] Initial import 
- [X] Retrieve and show Sonoff device list 
- [X] Show device state and provide ability to switch state


Builds on [sonoff-python](https://pypi.org/project/sonoff-python/)

## Installation instructions: 

1. Ensure you have [xbar](https://github.com/matryer/xbar/releases/latest) installed.
2. Copy [mysonoff.15m.py](mysonoff.15m.py) to your xbar plugins folder and chmod +x the file from your terminal in that folder
4. Run xbar

If you get a "websocket" error, perform the following: 

1. sudo easy_install -mxN websocket
2. sudo easy_install websocket_client
