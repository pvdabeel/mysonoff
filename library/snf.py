import websocket, logging, time, hmac, hashlib, random, base64, json, socket, requests, re, string

from datetime import timedelta
from websocket import create_connection

SCAN_INTERVAL = timedelta(seconds=60)

HTTP_CONTINUE                     = 100
HTTP_SWITCHING_PROTOCOLS          = 101
HTTP_PROCESSING                   = 102
HTTP_OK                           = 200
HTTP_CREATED                      = 201
HTTP_ACCEPTED                     = 202
HTTP_NON_AUTHORITATIVE            = 203
HTTP_NO_CONTENT                   = 204
HTTP_RESET_CONTENT                = 205
HTTP_PARTIAL_CONTENT              = 206
HTTP_MULTI_STATUS                 = 207
HTTP_MULTIPLE_CHOICES             = 300
HTTP_MOVED_PERMANENTLY            = 301
HTTP_MOVED_TEMPORARILY            = 302
HTTP_SEE_OTHER                    = 303
HTTP_NOT_MODIFIED                 = 304
HTTP_USE_PROXY                    = 305
HTTP_TEMPORARY_REDIRECT           = 307
HTTP_BAD_REQUEST                  = 400
HTTP_UNAUTHORIZED                 = 401
HTTP_PAYMENT_REQUIRED             = 402
HTTP_FORBIDDEN                    = 403
HTTP_NOT_FOUND                    = 404
HTTP_METHOD_NOT_ALLOWED           = 405
HTTP_NOT_ACCEPTABLE               = 406
HTTP_PROXY_AUTHENTICATION_REQUIRED= 407
HTTP_REQUEST_TIME_OUT             = 408
HTTP_CONFLICT                     = 409
HTTP_GONE                         = 410
HTTP_LENGTH_REQUIRED              = 411
HTTP_PRECONDITION_FAILED          = 412
HTTP_REQUEST_ENTITY_TOO_LARGE     = 413
HTTP_REQUEST_URI_TOO_LARGE        = 414
HTTP_UNSUPPORTED_MEDIA_TYPE       = 415
HTTP_RANGE_NOT_SATISFIABLE        = 416
HTTP_EXPECTATION_FAILED           = 417
HTTP_UNPROCESSABLE_ENTITY         = 422
HTTP_LOCKED                       = 423
HTTP_FAILED_DEPENDENCY            = 424
HTTP_INTERNAL_SERVER_ERROR        = 500
HTTP_NOT_IMPLEMENTED              = 501
HTTP_BAD_GATEWAY                  = 502
HTTP_SERVICE_UNAVAILABLE          = 503
HTTP_GATEWAY_TIME_OUT             = 504
HTTP_VERSION_NOT_SUPPORTED        = 505
HTTP_VARIANT_ALSO_VARIES          = 506
HTTP_INSUFFICIENT_STORAGE         = 507
HTTP_NOT_EXTENDED                 = 510

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)

def gen_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

class Sonoff():
    # def __init__(self, hass, email, password, api_region, grace_period):
    def __init__(self, username, password, api_region='eu', grace_period=60):

        self._username      = username
        self._password      = password
        self._api_region    = api_region
        self._wshost        = None

        self._skipped_login = 0
        self._grace_period  = timedelta(seconds=grace_period)

        self._user_apikey   = None
        self._devices       = []
        self._ws            = None

        self.do_login()

    def do_login(self):
        import uuid

        # reset the grace period
        self._skipped_login = 0
        
        self._model = 'iPhone' + random.choice(['6,1', '6,2', '7,1', '7,2', '8,1', '8,2', '8,4', '9,1', '9,2', '9,3', '9,4', '10,1', '10,2', '10,3', '10,4', '10,5', '10,6', '11,2', '11,4', '11,6', '11,8'])
        self._romVersion    = random.choice([
            '10.0', '10.0.2', '10.0.3', '10.1', '10.1.1', '10.2', '10.2.1', '10.3', '10.3.1', '10.3.2', '10.3.3', '10.3.4',
            '11.0', '11.0.1', '11.0.2', '11.0.3', '11.1', '11.1.1', '11.1.2', '11.2', '11.2.1', '11.2.2', '11.2.3', '11.2.4', '11.2.5', '11.2.6', '11.3', '11.3.1', '11.4', '11.4.1',
            '12.0', '12.0.1', '12.1', '12.1.1', '12.1.2', '12.1.3', '12.1.4', '12.2', '12.3', '12.3.1', '12.3.2', '12.4', '12.4.1', '12.4.2',
            '13.0', '13.1', '13.1.1', '13.1.2', '13.2'
        ])
        self._appVersion    = random.choice(['3.5.3', '3.5.4', '3.5.6', '3.5.8', '3.5.10', '3.5.12', '3.6.0', '3.6.1', '3.7.0', '3.8.0', '3.9.0', '3.9.1', '3.10.0', '3.11.0'])

        self._imei = str(uuid.uuid4())

        app_details = {
            'password'  : self._password,
            'version'   : '6',
            'ts'        : int(time.time()),
            'nonce'     : gen_nonce(15), #''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8)), #gen_nonce(15),
            'appid'     : 'oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq',
            'imei'      : self._imei,
            'os'        : 'iOS',
            'model'     : self._model,
            'romVersion': self._romVersion,
            'appVersion': self._appVersion
        }

        if re.match(r'[^@]+@[^@]+\.[^@]+', self._username):
            app_details['email'] = self._username
        else:
            app_details['phoneNumber'] = self._username

        decryptedAppSecret = b'6Nz4n0xA8s8qdxQf2GqurZj2Fs55FUvM'

        hex_dig = hmac.new(
            decryptedAppSecret, 
            str.encode(json.dumps(app_details)), 
            digestmod=hashlib.sha256).digest()
        
        sign = base64.b64encode(hex_dig).decode()

        self._headers = {
            'Authorization' : 'Sign ' + sign,
            'Content-Type'  : 'application/json;charset=UTF-8'
        }

        r = requests.post('https://{}-api.coolkit.cc:8080/api/user/login'.format(self._api_region), 
            headers=self._headers, json=app_details)



        resp = r.json()
        

        # get a new region to login
        if 'error' in resp and 'region' in resp and resp['error'] == HTTP_MOVED_PERMANENTLY:
            self._api_region    = resp['region']

            _LOGGER.warning("found new region: >>> %s <<< (you should change api_region option to this value in configuration.yaml)", self._api_region)

            # re-login using the new localized endpoint
            self.do_login()
            return

        elif 'error' in resp and resp['error'] in [HTTP_NOT_FOUND, HTTP_BAD_REQUEST]:
            # (most likely) login with +86... phone number and region != cn
            if '@' not in self._username and self._api_region != 'cn':
                self._api_region    = 'cn'
                self.do_login()

            else:
                _LOGGER.error("Couldn't authenticate using the provided credentials!")

            return

        self._bearer_token  = resp['at']
        self._user_apikey   = resp['user']['apikey']
        self._headers.update({'Authorization' : 'Bearer ' + self._bearer_token})

        # get the websocket host
        if not self._wshost:
            self.set_wshost()

        self.update_devices() # to get the devices list 

    def set_wshost(self):
        r = requests.post('https://%s-disp.coolkit.cc:8080/dispatch/app' % self._api_region, headers=self._headers)
        resp = r.json()

        if 'error' in resp and resp['error'] == 0 and 'domain' in resp:
            self._wshost = resp['domain']
            _LOGGER.info("Found websocket address: %s", self._wshost)
        else:
            raise Exception('No websocket domain')

    def is_grace_period(self):
        grace_time_elapsed = self._skipped_login * int(SCAN_INTERVAL.total_seconds()) 
        grace_status = grace_time_elapsed < int(self._grace_period.total_seconds())

        if grace_status:
            self._skipped_login += 1

        return grace_status

    def update_devices(self):

        # the login failed, nothing to update
        if not self._wshost:
            return []

        # we are in the grace period, no updates to the devices
        if self._skipped_login and self.is_grace_period():          
            _LOGGER.info("Grace period active")            
            return self._devices

#        r = requests.get('https://{}-api.coolkit.cc:8080/api/user/device'.format(self._api_region), 
#            headers=self._headers)


        r = requests.get('https://{}-api.coolkit.cc:8080/api/user/device?lang=en&apiKey={}&getTags=1&version=6&ts=%s&nonce=%s&appid=oeVkj2lYFGnJu5XUtWisfW4utiN4u9Mq&imei=%s&os=iOS&model=%s&romVersion=%s&appVersion=%s'.format(self._api_region, self.get_user_apikey(), str(int(time.time())), ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8)), self._imei, self._model, self._romVersion, self._appVersion), headers=self._headers)

        resp = r.json()
        if 'error' in resp and resp['error'] in [HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED]:
            # @IMPROVE add maybe a service call / switch to deactivate sonoff component
            if self.is_grace_period():
                _LOGGER.warning("Grace period activated!")

                # return the current (and possible old) state of devices
                # in this period any change made with the mobile app (on/off) won't be shown in HA
                return self._devices

            _LOGGER.info("Re-login component")
            self.do_login()

        self._devices = r.json()['devicelist'] if 'devicelist' in r.json() else r.json()
        return self._devices

    def get_devices(self, force_update = False):
        if force_update: 
            return self.update_devices()

        return self._devices

    def get_device(self, deviceid):
        for device in self.get_devices():
            if 'deviceid' in device and device['deviceid'] == deviceid:
                return device

    def get_bearer_token(self):
        return self._bearer_token

    def get_user_apikey(self):
        return self._user_apikey

    def get_model(self):
        return self._model

    def get_romVersion(self):
        return self._romVersion

    def get_wshost(self):
        return self._wshost


    def _get_ws(self):
        """Check if the websocket is setup and connected."""
        try:
            create_connection
        except:
            from websocket import create_connection

        if self._ws is None:
            try:
                self._ws = create_connection(('wss://{}:8080/api/ws'.format(self._wshost)), timeout=10)

                payload = {
                    'action'    : "userOnline",
                    'userAgent' : 'app',
                    'version'   : 6,
                    'nonce'     : gen_nonce(15),
                    'apkVesrion': "1.8",
                    'os'        : 'iOS',
                    'at'        : self.get_bearer_token(),
                    'apikey'    : self.get_user_apikey(),
                    'ts'        : str(int(time.time())),
                    'model'     : self.get_model(),
                    'romVersion': self.get_romVersion(),
                    'sequence'  : str(time.time()).replace('.','')
                }

                self._ws.send(json.dumps(payload))

                wsresp = self._ws.recv()
                # _LOGGER.error("open socket: %s", wsresp)

            except (socket.timeout):
                _LOGGER.error('failed to create the websocket')
                self._ws = None

        return self._ws
        
    def switch(self, new_state, deviceid, outlet):
        """Switch on or off."""

        # we're in the grace period, no state change
        if self._skipped_login:
            _LOGGER.info("Grace period, no state change")
            return (not new_state)

        self._ws = self._get_ws()
        
        if not self._ws:
            _LOGGER.warning('invalid websocket, state cannot be changed')
            return (not new_state)

        # convert from True/False to on/off
        if isinstance(new_state, (bool)):
            new_state = 'on' if new_state else 'off'

        device = self.get_device(deviceid)

        if outlet is not None:
            _LOGGER.debug("Switching `%s - %s` on outlet %d to state: %s", \
                device['deviceid'], device['name'] , (outlet+1) , new_state)
        else:
            _LOGGER.debug("Switching `%s` to state: %s", deviceid, new_state)

        if not device:
            _LOGGER.error('unknown device to be updated')
            return False

        # the payload rule is like this:
        #   normal device (non-shared) 
        #       apikey      = login apikey (= device apikey too)
        #
        #   shared device
        #       apikey      = device apikey
        #       selfApiKey  = login apikey (yes, it's typed corectly selfApikey and not selfApiKey :|)

        if outlet is not None:
            params = { 'switches' : device['params']['switches'] }
            params['switches'][outlet]['switch'] = new_state
        else:
            params = { 'switch' : new_state }

        payload = {
            'action'        : 'update',
            'userAgent'     : 'app',
            'params'        : params,
            'apikey'        : device['apikey'],
            'deviceid'      : str(deviceid),
            'sequence'      : str(time.time()).replace('.',''),
            'controlType'   : device['params']['controlType'] if 'controlType' in device['params'] else 4,
            'ts'            : 0
        }

        # this key is needed for a shared device
        if device['apikey'] != self.get_user_apikey():
            payload['selfApikey'] = self.get_user_apikey()

        self._ws.send(json.dumps(payload))
        wsresp = self._ws.recv()
        # _LOGGER.debug("switch socket: %s", wsresp)
        
        self._ws.close() # no need to keep websocket open (for now)
        self._ws = None

        # set also te pseudo-internal state of the device until the real refresh kicks in
        for idx, device in enumerate(self._devices):
            if device['deviceid'] == deviceid:
                if outlet is not None:
                    self._devices[idx]['params']['switches'][outlet]['switch'] = new_state
                else:
                    self._devices[idx]['params']['switch'] = new_state

        return new_state

