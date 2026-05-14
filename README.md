
# MySonoff - MacOS Menubar plugin

Displays information about your Sonoff switches in the MacOS menubar. Allows you to control the switches in your home via the Ewelink API.

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

0. Install [Python 3](http://www.python.org) (3.8 or newer). The default shebang points at `/opt/local/bin/python3` (MacPorts); adjust if you use Homebrew or pyenv.
1. Install the runtime dependencies: `pip3 install keyring requests websocket-client`
2. Ensure you have [xbar](https://github.com/matryer/xbar/releases/latest) installed.
3. Copy [mysonoff.15m.py](mysonoff.15m.py) (and the `library/` folder next to it) to your xbar plugins folder, then `chmod +x mysonoff.15m.py`.
4. Run xbar.

On first launch click *Login to Sonoff* to store your credentials in the macOS Keychain. The plugin keeps a short-lived session cache under `~/.state/mysonoff/` so most refreshes skip the login round-trip.

If you get a `websocket` error, make sure you installed `websocket-client` (not the older `websocket` package):

```
pip3 uninstall -y websocket
pip3 install --upgrade websocket-client
```
