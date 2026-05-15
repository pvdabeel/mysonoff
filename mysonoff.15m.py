#!/usr/bin/env PYTHONIOENCODING=UTF-8 /opt/local/bin/python3
# -*- coding: utf-8 -*-
#
# <xbar.title>MySonoff</xbar.title>
# <xbar.version>v1.1</xbar.version>
# <xbar.author>pvdabeel@mac.com</xbar.author>
# <xbar.author.github>pvdabeel</xbar.author.github>
# <xbar.desc>Control your Sonoff switches from the MacOS menubar</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
#
# Licence: GPL v3

# Installation instructions:
# --------------------------
# Execute in terminal.app before running:
#    pip3 install keyring requests websocket-client
#
# Ensure you have xbar installed https://github.com/matryer/xbar/releases/latest
# Copy this file to your xbar plugins folder and chmod +x the file from your terminal in that folder
# Run xbar

import getpass
import json
import os
import sys
import time
from os.path import expanduser
from urllib.error import HTTPError, URLError

import keyring

import library.snf as sonoff


_DEBUG_ = False

# Location where to store state files
HOME = expanduser("~")
STATE_DIR = os.path.join(HOME, ".state", "mysonoff")
CACHE_FILE = os.path.join(STATE_DIR, "session.json")

# How long a cached session/device list is considered fresh.
# Re-authenticating on every 15-minute xbar refresh is wasteful and slow,
# so we persist the bearer token, websocket host and the device snapshot.
SESSION_TTL_SECONDS = 6 * 60 * 60       # bearer token reuse window
DEVICE_CACHE_TTL_SECONDS = 60           # device list freshness window

os.makedirs(STATE_DIR, exist_ok=True)

# The full path to this file
CMD_PATH = os.path.realpath(__file__)

# Nice ANSI colors
CEND = '\33[0m'
CRED = '\33[31m'
CGREEN = '\33[32m'
CYELLOW = '\33[33m'
CBLUE = '\33[36m'

# Support for OS X Dark Mode
DARK_MODE = os.getenv('XBARDarkMode', 'false') == 'true'

KEYRING_SERVICE = "mysonoff-bitbar"


# --------------------------
# Pretty printing
# --------------------------

def justify(string, number=10):
    length = len(string)
    quot = (number - length) // 4
    rem = (number - length) % 4
    return string.ljust(length + rem, ' ').ljust(length + rem + quot, '\t')


# Logo for both dark mode and regular mode
LOGO_DARK = 'iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAAAXNSR0IArs4c6QAAAIRlWElmTU0AKgAAAAgABQESAAMAAAABAAEAAAEaAAUAAAABAAAASgEbAAUAAAABAAAAUgEoAAMAAAABAAIAAIdpAAQAAAABAAAAWgAAAAAAAACQAAAAAQAAAJAAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAACSgAwAEAAAAAQAAACQAAAAAODYCaQAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAVlpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDUuNC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KTMInWQAAA11JREFUWAndmD1oFFEQx73EKH4SkICdiKWVdhqJFiKkEEsRe1uxskgtFhZqoVhZCdqLRQpRA0IQO1Ek2FkoiBoQEc0l5++3twN7l739eAQDDvxv5r353Hlzu3vX2VJCvV5vrNPprMF3oJ4GE6BXYtpmq4PxCnhJ7F+RozaAhhrBp8AHsNFkzKk8R5arWNTW4iKXx+Fr4BI4BE6Cz2A7cD+FTPwb7AcvgLGvgciF2KeygkK3D2GZ9i7ExgbwJbqzTBxjl1JVQat4TBBAG+Vor7PkPDShoq3dtSPOo/FKqaogkxpwlS45R2s5N6j7oor0x6Wziq/cGBZSLHKdf1VBA8Z5QAOPvLoBh7zgKGZIN3LZuCACj1sMfIZoN8EeMKpLducHuILPQviyrqXGBREp5uY68hHwEOwCw0Vp9xNcANp6HwtfxGpqU1AktojHXPnFqtB0ZTf6A7lN+Fa5ZLo2BUUwg+90QVLvTcMz5dF6z9GmcSHYZpRSkI6RqOtc9UP1PykydMGL6lo57i21hv/K4L8rqOzbU7bXuMGpMxRJxxgZ79xFiq6HTVFXK6cUZKI/RmagMz6UJYZcXeuiUgryDnyazjyDd4Ex/PpLft1j7zjyKzfbULS3jY+2+vn2dwwcBBYhlN1TlxQ7xWkvyeY5rjPwJXAHeUYou5fr5pG1bUUpR2YnJvMs5+DLHF8kvsf6Ua7TRttWlNKh72SYpoizdOIjcKYeCGX31GkDtG1FKR2yG2/Bk0KmuYKsqE6b6Jx7jSilQ9uIbGf8mfQazCG/EcruqdMGaNuKUjpkgnhw3kV+V8j4FPlTvg6bgrpeTCnIuZilEyfoxH1TIN+Ws74MW1QHnwXPQStKKchfDd+AMxK0GELO1WmjbStqU1A8Bnx2+RP7Bp2Ygns02beJ9Xlk7b4AbeI5F75sVVObgmImrhLyFjgFvM+YLBL7HNPuMHgPtJXCt7+q+GxcEPMRv68WiHe0IuaAiq7hOvhWOWAwtGhcUB4Ylr1ueMV1V23nsmLCdyh36bKqIBNmx0FAj8J3H4PEfpO5wKX/vgT33uTR6jfyYqoK0nmFS4znUbznsJ1MXQrzTSBmbl2gqoK+Yj1JAJ/iG/l3jA9dYzcjCsgeJ/BN+cOqdA4siqPalL/0/gKkeO/loYY4BQAAAABJRU5ErkJggg=='

LOGO_LIGHT = 'iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAAAXNSR0IArs4c6QAAAIRlWElmTU0AKgAAAAgABQESAAMAAAABAAEAAAEaAAUAAAABAAAASgEbAAUAAAABAAAAUgEoAAMAAAABAAIAAIdpAAQAAAABAAAAWgAAAAAAAACQAAAAAQAAAJAAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAACSgAwAEAAAAAQAAACQAAAAAODYCaQAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAVlpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDUuNC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KTMInWQAAAzFJREFUWAndmDtoFUEUhhPjA58IErATsbTSTiPRQgQLsRSxtxUrC2uxsFALxcpK0F4sLEQTCIjYiSIhnYWC+AAR0fj6Pu8eXTd7Z3cmFwsP/HfOzvznnP+enZ29yfhYu61g+jtYC6bAKvADLMfGCV4Ec+ATiBq4aZOoTYIFoJBRwpzm1qLW4IrPlb+9P84Ert05CXaA/eAVWAOcLzELfwZbwQww9zkQtXAH1iYo1rbgvAezMTGCcb7Kae5WSwn6RoR7R45+tNfb537oY3Wu3bUj5jRfq6UEWdSEBjua0NGkjiJlxgvjm7m8brWUoGaAAqJAc63tOgSHmDbOkrkcQXbGbzsNLoKNIIri/mWK+ABOA/dgxOKmLUdQtPk8KXeBm2A9aIqS9xEcB3I9xyIWN205gqKwIm6DE+nUYxtY31ZxIrYjpP0c6goy+bqK5NnUfGK8PZ45cnoLgfvLcjoUMY5R6Ct+U1CsxViP6/TjbOkk/ivCfyeo7elpm+vd4NI9FEXtsJu4btH14NTXOv0SQRb6UmWOsV4oNrlr2aJKBHkCHwT3gU+ZOXz8NR/3mNuL/8jJHIv25sTINc5ff3vAdqAIoe+ca0W5S4I2UewuOATmwRXg+03oO+eaHLlZVnLL7MTmqspRRn/EReFr+LeqNTlys6ykQ++o4AvzCHgB3FM3Kug755ocuVlW0iG78RTcqVU6W/N1XZMTnXOul5V0aDWZ7YK/IB8DxTypoO+ca3LkZllJhywQL86r+M9qFe/hv6yug1Nb7nZLBLkvDoN94HpV4nI1nmJ8CFyT8wBkWYkg/2p4C9wjYYqom2ty5GZZjqB4DUxQwT+xL4BJ4K2Jp+kYvrzXQI5cLWIHV4nPHEGxJ86Q7xI4ADxnLBaFfY/J2wmeA7laxA6uEp85gixm8VmwO5GzuWRMvHCba0uucwSZ2G9qNxy7vrX8EBOxTKUtJciCJlKA3zDOrJh3rcvkxu30bNJPiksJMngRxPuod9uJGWbmMmeIXMJLCXoD2xfkNBjlv2PMae7eFrfGR3oB2PZRwpzm1qLW4IrPYftAovfcs2QKeMApajlmLW/XHBj6L72fdknNe6HtIn8AAAAASUVORK5CYII='


def app_print_logo():
    print(f'|image={LOGO_DARK if DARK_MODE else LOGO_LIGHT}')
    print('---')


# --------------------------
# Session cache (avoids re-login on every xbar refresh)
# --------------------------

def _load_cache():
    try:
        with open(CACHE_FILE, 'r') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _save_cache(data):
    try:
        with open(CACHE_FILE, 'w') as fh:
            json.dump(data, fh)
        os.chmod(CACHE_FILE, 0o600)
    except OSError:
        pass


def _is_fresh(cache, key, ttl):
    if not cache or key not in cache:
        return False
    return (time.time() - cache[key]) < ttl


def _build_client(username, password):
    """Return a Sonoff client, reusing a cached session when possible."""
    cache = _load_cache()

    if cache and _is_fresh(cache, 'session_ts', SESSION_TTL_SECONDS):
        # grace_period=0: this script runs as a one-shot xbar refresh, so any
        # rejected bearer token should re-login immediately rather than fall
        # into the HA-style backoff that silently returns an empty device list.
        client = sonoff.Sonoff.from_session(
            username=username,
            password=password,
            api_region=cache.get('api_region', 'eu'),
            bearer_token=cache['bearer_token'],
            user_apikey=cache['user_apikey'],
            wshost=cache['wshost'],
            model=cache.get('model'),
            rom_version=cache.get('rom_version'),
            app_version=cache.get('app_version'),
            imei=cache.get('imei'),
            grace_period=0,
        )

        # Only trust the cached device list if it's both fresh AND non-empty;
        # otherwise a previous failed refresh that stored [] would silently
        # blank the menu for the rest of the TTL window.
        cached_devices = cache.get('devices')
        if (
            _is_fresh(cache, 'devices_ts', DEVICE_CACHE_TTL_SECONDS)
            and cached_devices
        ):
            client._devices = cached_devices
            return client, cache

        try:
            client.update_devices()
            # update_devices() may have transparently re-logged in if the
            # cached bearer token was rejected; refresh the cache from the
            # client so the next run picks up the new credentials.
            cache['api_region'] = client._api_region
            cache['bearer_token'] = client.get_bearer_token()
            cache['user_apikey'] = client.get_user_apikey()
            cache['wshost'] = client.get_wshost()
            cache['session_ts'] = time.time()
            cache['devices'] = client._devices
            cache['devices_ts'] = time.time()
            _save_cache(cache)
            return client, cache
        except Exception:
            # cached token rejected -> fall through to fresh login
            pass

    client = sonoff.Sonoff(username, password, 'eu')
    cache = {
        'api_region': client._api_region,
        'bearer_token': client.get_bearer_token(),
        'user_apikey': client.get_user_apikey(),
        'wshost': client.get_wshost(),
        'model': client.get_model(),
        'rom_version': client.get_romVersion(),
        'app_version': client.get_appVersion(),
        'imei': client._imei,
        'session_ts': time.time(),
        'devices': client._devices,
        'devices_ts': time.time(),
    }
    _save_cache(cache)
    return client, cache


# --------------------------
# init: store credentials in keychain on first launch
# --------------------------

def init():
    print('Enter your Sonoff username:')
    init_username = input()
    print('Enter your Sonoff password:')
    init_password = getpass.getpass()

    try:
        sonoff.Sonoff(init_username, init_password, 'eu')
    except HTTPError as e:
        print('Error contacting Sonoff servers. Try again later.')
        print(e)
        time.sleep(0.5)
        return
    except URLError as e:
        print('Error: Unable to connect. Check your connection settings.')
        print(e)
        return
    except AttributeError as e:
        print('Error: Could not get an access token from Sonoff. Try again later.')
        print(e)
        return

    keyring.set_password(KEYRING_SERVICE, "username", init_username)
    keyring.set_password(KEYRING_SERVICE, "password", init_password)

    # Drop any stale cached session so the next refresh re-authenticates cleanly.
    try:
        os.remove(CACHE_FILE)
    except OSError:
        pass


USERNAME = keyring.get_password(KEYRING_SERVICE, "username")


# --------------------------
# Menu rendering helpers
# --------------------------

def _print_switch_row(label, state, devid, target_state, color, outlet=None):
    """Emit the two xbar lines (default + alternate) for one switch row."""
    state_color = CGREEN if state == 'on' else CRED
    label_padded = justify(label, 41)
    outlet_param = f' param4={outlet}' if outlet is not None else ''

    common = (
        f'{label_padded}{state_color}{state}{CEND} | refresh=true '
        f'shell="{CMD_PATH}" param1=switch param2={devid} param3={target_state}'
        f'{outlet_param} color={color}'
    )
    print(f'{common} terminal=false')
    print(f'{common} terminal=true alternate=true')


# --------------------------
# Main
# --------------------------

def main(argv):
    # CASE 1: init was called
    if 'init' in argv:
        init()
        return

    # Debug runs always start from a clean slate so the output reflects a
    # real round-trip to the API rather than whatever happens to be cached.
    if 'debug' in argv:
        try:
            os.remove(CACHE_FILE)
            print(f">>> removed cache: {CACHE_FILE}")
        except FileNotFoundError:
            print(f">>> no cache to remove at {CACHE_FILE}")
        except OSError as exc:
            print(f">>> could not remove cache: {exc}")

    # CASE 2: init was not called, keyring not initialized
    if DARK_MODE:
        color = '#FFFFFE'
    else:
        color = '#00000E'

    if not USERNAME:
        app_print_logo()
        print(
            f'Login to Sonoff | refresh=true terminal=true '
            f'shell="{CMD_PATH}" param1=init color={color}'
        )
        return

    # CASE 3: init was called, keyring initialized but connection failed
    try:
        password = keyring.get_password(KEYRING_SERVICE, "password")
        client, cache = _build_client(USERNAME, password)
        devices = client.get_devices()
    except Exception:
        app_print_logo()
        print(
            f'Login to Sonoff | refresh=true terminal=true '
            f'shell="{CMD_PATH}" param1=init color={color}'
        )
        return

    # CASE 4: specific switch command received
    if len(argv) > 1 and 'debug' not in argv:
        if argv[1] == "switch":
            if len(argv) == 4:
                client.switch(argv[3], argv[2], None)
            elif len(argv) == 5:
                client.switch(argv[3], argv[2], int(argv[4]))
            else:
                print('Wrong number of arguments: switch <id> <state:on/off> <optional:outlet>')
                return

            # Persist the optimistic state update so the next refresh shows it instantly.
            cache['devices'] = client._devices
            cache['devices_ts'] = time.time()
            _save_cache(cache)
        return

    # CASE 5: render the menu
    app_print_logo()

    # DEBUG menu
    if 'debug' in argv:
        print(f">>> api_region: {client._api_region}")
        print(f">>> wshost:     {client.get_wshost()}")
        print(f">>> devices ({type(devices).__name__}, len="
              f"{len(devices) if hasattr(devices, '__len__') else '?'}):")
        if isinstance(devices, list):
            for d in devices:
                if isinstance(d, dict):
                    name = d.get('name', '?')
                    params = d.get('params', {}) or {}
                    state = params.get('switch') or params.get('switches')
                    print(f"    - {d.get('deviceid', '?')}  {name}  -> {state}")
                else:
                    print(f"    - {d!r}")
        else:
            print(f"    raw: {devices!r}")
        return

    devices_ordered = sorted(devices, key=lambda d: d['name'])

    for d in devices_ordered:
        outlets = d['uiid']
        devid = d['deviceid']
        name = d['name']
        params = d.get('params', {})

        switches = params.get('switches')
        if switches:
            for idx, sw in enumerate(switches):
                if idx >= outlets:
                    break
                state = sw['switch']
                outlet_label = f"{name} (outlet {idx + 1})\t"
                target = 'off' if state == 'on' else 'on'
                _print_switch_row(outlet_label, state, devid, target, color, outlet=idx)
        elif 'switch' in params:
            state = params['switch']
            target = 'off' if state == 'on' else 'on'
            _print_switch_row(name, state, devid, target, color)


if __name__ == '__main__':
    main(sys.argv)
