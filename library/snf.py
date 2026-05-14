import base64
import hashlib
import hmac
import json
import logging
import random
import re
import socket
import string
import time
import uuid
from datetime import timedelta

import requests
from websocket import create_connection

SCAN_INTERVAL = timedelta(seconds=60)

# Only the HTTP status codes the Sonoff endpoints actually return for us.
HTTP_OK = 200
HTTP_MOVED_PERMANENTLY = 301
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)

# Static client fingerprint pools. Picked once per Sonoff() instance.
_IPHONE_MODELS = (
    '6,1', '6,2', '7,1', '7,2', '8,1', '8,2', '8,4',
    '9,1', '9,2', '9,3', '9,4',
    '10,1', '10,2', '10,3', '10,4', '10,5', '10,6',
    '11,2', '11,4', '11,6', '11,8',
)

_ROM_VERSIONS = (
    '10.0', '10.0.2', '10.0.3', '10.1', '10.1.1', '10.2', '10.2.1',
    '10.3', '10.3.1', '10.3.2', '10.3.3', '10.3.4',
    '11.0', '11.0.1', '11.0.2', '11.0.3', '11.1', '11.1.1', '11.1.2',
    '11.2', '11.2.1', '11.2.2', '11.2.3', '11.2.4', '11.2.5', '11.2.6',
    '11.3', '11.3.1', '11.4', '11.4.1',
    '12.0', '12.0.1', '12.1', '12.1.1', '12.1.2', '12.1.3', '12.1.4',
    '12.2', '12.3', '12.3.1', '12.3.2', '12.4', '12.4.1', '12.4.2',
    '13.0', '13.1', '13.1.1', '13.1.2', '13.2',
)

_APP_VERSIONS = (
    '3.5.3', '3.5.4', '3.5.6', '3.5.8', '3.5.10', '3.5.12',
    '3.6.0', '3.6.1', '3.7.0', '3.8.0', '3.9.0', '3.9.1', '3.10.0', '3.11.0',
)

_APPID = 'oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq'
_APP_SECRET = b'6Nz4n0xA8s8qdxQf2GqurZj2Fs55FUvM'

_DIGITS = string.digits
_LC_DIGITS = string.ascii_lowercase + string.digits


def gen_nonce(length=8):
    """Generate a pseudo-random numeric nonce."""
    return ''.join(random.choices(_DIGITS, k=length))


def _gen_alnum_nonce(length=8):
    return ''.join(random.choices(_LC_DIGITS, k=length))


class Sonoff:
    def __init__(self, username, password, api_region='eu', grace_period=60):
        self._username = username
        self._password = password
        self._api_region = api_region
        self._wshost = None

        self._skipped_login = 0
        self._grace_period = timedelta(seconds=grace_period)

        self._user_apikey = None
        self._bearer_token = None
        self._headers = {}
        self._devices = []
        self._ws = None

        # Reuse a single TCP connection across the login -> dispatch -> devices calls.
        self._session = requests.Session()

        self._model = 'iPhone' + random.choice(_IPHONE_MODELS)
        self._romVersion = random.choice(_ROM_VERSIONS)
        self._appVersion = random.choice(_APP_VERSIONS)
        self._imei = str(uuid.uuid4())

        self.do_login()

    @classmethod
    def from_session(cls, username, password, api_region, bearer_token,
                     user_apikey, wshost, model=None, rom_version=None,
                     app_version=None, imei=None, grace_period=60):
        """Build a Sonoff client from a previously cached session.

        Skips the initial login round-trip; ``update_devices`` will fall back
        to ``do_login`` automatically if the cached token has expired.
        """
        self = cls.__new__(cls)
        self._username = username
        self._password = password
        self._api_region = api_region
        self._wshost = wshost

        self._skipped_login = 0
        self._grace_period = timedelta(seconds=grace_period)

        self._user_apikey = user_apikey
        self._bearer_token = bearer_token
        self._devices = []
        self._ws = None
        self._session = requests.Session()

        self._model = model or ('iPhone' + random.choice(_IPHONE_MODELS))
        self._romVersion = rom_version or random.choice(_ROM_VERSIONS)
        self._appVersion = app_version or random.choice(_APP_VERSIONS)
        self._imei = imei or str(uuid.uuid4())

        self._headers = {
            'Authorization': 'Bearer ' + bearer_token,
            'Content-Type': 'application/json;charset=UTF-8',
        }
        return self

    # --------------------------
    # Authentication
    # --------------------------

    def do_login(self):
        self._skipped_login = 0

        app_details = {
            'password': self._password,
            'version': '6',
            'ts': int(time.time()),
            'nonce': gen_nonce(15),
            'appid': _APPID,
            'imei': self._imei,
            'os': 'iOS',
            'model': self._model,
            'romVersion': self._romVersion,
            'appVersion': self._appVersion,
        }

        if re.match(r'[^@]+@[^@]+\.[^@]+', self._username):
            app_details['email'] = self._username
        else:
            app_details['phoneNumber'] = self._username

        body = json.dumps(app_details)
        sign = base64.b64encode(
            hmac.new(_APP_SECRET, body.encode(), digestmod=hashlib.sha256).digest()
        ).decode()

        self._headers = {
            'Authorization': 'Sign ' + sign,
            'Content-Type': 'application/json;charset=UTF-8',
        }

        r = self._session.post(
            f'https://{self._api_region}-api.coolkit.cc:8080/api/user/login',
            headers=self._headers,
            data=body,
            timeout=10,
        )
        resp = r.json()

        # follow region redirect
        if 'error' in resp and resp.get('error') == HTTP_MOVED_PERMANENTLY and 'region' in resp:
            self._api_region = resp['region']
            _LOGGER.warning(
                "found new region: >>> %s <<< (update api_region accordingly)",
                self._api_region,
            )
            self.do_login()
            return

        if 'error' in resp and resp['error'] in (HTTP_NOT_FOUND, HTTP_BAD_REQUEST):
            # phone-number login defaults to cn region
            if '@' not in self._username and self._api_region != 'cn':
                self._api_region = 'cn'
                self.do_login()
            else:
                _LOGGER.error("Couldn't authenticate using the provided credentials!")
            return

        self._bearer_token = resp['at']
        self._user_apikey = resp['user']['apikey']
        self._headers['Authorization'] = 'Bearer ' + self._bearer_token

        if not self._wshost:
            self.set_wshost()

        self.update_devices()

    def set_wshost(self):
        r = self._session.post(
            f'https://{self._api_region}-disp.coolkit.cc:8080/dispatch/app',
            headers=self._headers,
            timeout=10,
        )
        resp = r.json()

        if resp.get('error') == 0 and 'domain' in resp:
            self._wshost = resp['domain']
            _LOGGER.info("Found websocket address: %s", self._wshost)
        else:
            raise Exception('No websocket domain')

    def is_grace_period(self):
        elapsed = self._skipped_login * int(SCAN_INTERVAL.total_seconds())
        active = elapsed < int(self._grace_period.total_seconds())
        if active:
            self._skipped_login += 1
        return active

    # --------------------------
    # Devices
    # --------------------------

    def _devices_url(self):
        params = {
            'lang': 'en',
            'apiKey': self._user_apikey,
            'getTags': '1',
            'version': '6',
            'ts': str(int(time.time())),
            'nonce': _gen_alnum_nonce(8),
            'appid': _APPID,
            'imei': self._imei,
            'os': 'iOS',
            'model': self._model,
            'romVersion': self._romVersion,
            'appVersion': self._appVersion,
        }
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        return (
            f'https://{self._api_region}-api.coolkit.cc:8080/api/user/device?{query}'
        )

    def update_devices(self):
        if not self._wshost:
            return []

        if self._skipped_login and self.is_grace_period():
            _LOGGER.info("Grace period active")
            return self._devices

        r = self._session.get(self._devices_url(), headers=self._headers, timeout=10)
        resp = r.json()

        if 'error' in resp and resp['error'] in (HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED):
            if self.is_grace_period():
                _LOGGER.warning("Grace period activated!")
                return self._devices

            _LOGGER.info("Re-login component")
            self.do_login()
            return self._devices

        if isinstance(resp, dict) and 'devicelist' in resp:
            self._devices = resp['devicelist']
        else:
            self._devices = resp
        return self._devices

    def get_devices(self, force_update=False):
        if force_update:
            return self.update_devices()
        return self._devices

    def get_device(self, deviceid):
        for device in self.get_devices():
            if device.get('deviceid') == deviceid:
                return device
        return None

    # --------------------------
    # Accessors
    # --------------------------

    def get_bearer_token(self):
        return self._bearer_token

    def get_user_apikey(self):
        return self._user_apikey

    def get_model(self):
        return self._model

    def get_romVersion(self):
        return self._romVersion

    def get_appVersion(self):
        return self._appVersion

    def get_wshost(self):
        return self._wshost

    # --------------------------
    # Websocket / state changes
    # --------------------------

    def _get_ws(self):
        """Open and authenticate the control websocket if needed."""
        if self._ws is not None:
            return self._ws

        try:
            self._ws = create_connection(
                f'wss://{self._wshost}:8080/api/ws', timeout=10
            )

            payload = {
                'action': 'userOnline',
                'userAgent': 'app',
                'version': 6,
                'nonce': gen_nonce(15),
                'apkVesrion': '1.8',
                'os': 'iOS',
                'at': self._bearer_token,
                'apikey': self._user_apikey,
                'ts': str(int(time.time())),
                'model': self._model,
                'romVersion': self._romVersion,
                'sequence': str(time.time()).replace('.', ''),
            }

            self._ws.send(json.dumps(payload))
            self._ws.recv()
        except (socket.timeout, OSError) as exc:
            _LOGGER.error('failed to create the websocket: %s', exc)
            self._ws = None

        return self._ws

    def switch(self, new_state, deviceid, outlet):
        """Switch a device on or off (optionally targeting a specific outlet)."""
        if self._skipped_login:
            _LOGGER.info("Grace period, no state change")
            return not new_state

        ws = self._get_ws()
        if not ws:
            _LOGGER.warning('invalid websocket, state cannot be changed')
            return not new_state

        if isinstance(new_state, bool):
            new_state = 'on' if new_state else 'off'

        device = self.get_device(deviceid)
        if not device:
            _LOGGER.error('unknown device to be updated')
            return False

        if outlet is not None:
            _LOGGER.debug(
                "Switching `%s - %s` on outlet %d to state: %s",
                device['deviceid'], device['name'], (outlet + 1), new_state,
            )
            params = {'switches': device['params']['switches']}
            params['switches'][outlet]['switch'] = new_state
        else:
            _LOGGER.debug("Switching `%s` to state: %s", deviceid, new_state)
            params = {'switch': new_state}

        # The payload rules:
        #   normal device (non-shared): apikey == user apikey == device apikey
        #   shared device:              apikey == device apikey,
        #                               selfApikey (sic) == user apikey
        payload = {
            'action': 'update',
            'userAgent': 'app',
            'params': params,
            'apikey': device['apikey'],
            'deviceid': str(deviceid),
            'sequence': str(time.time()).replace('.', ''),
            'controlType': device['params'].get('controlType', 4),
            'ts': 0,
        }

        if device['apikey'] != self._user_apikey:
            payload['selfApikey'] = self._user_apikey

        ws.send(json.dumps(payload))
        ws.recv()

        ws.close()
        self._ws = None

        # Optimistically update the cached device state until the next refresh.
        for idx, dev in enumerate(self._devices):
            if dev['deviceid'] != deviceid:
                continue
            if outlet is not None:
                self._devices[idx]['params']['switches'][outlet]['switch'] = new_state
            else:
                self._devices[idx]['params']['switch'] = new_state
            break

        return new_state
