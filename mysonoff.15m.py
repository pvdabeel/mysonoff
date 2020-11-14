#!/usr/bin/env PYTHONIOENCODING=UTF-8 /usr/bin/python
# -*- coding: utf-8 -*-
#
# <bitbar.title>MySonoff</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>pvdabeel@mac.com</bitbar.author>
# <bitbar.author.github>pvdabeel</bitbar.author.github>
# <bitbar.desc>Control your Sonoff switches from the Mac OS X menubar</bitbar.desc>
# <bitbar.dependencies>python</bitbar.dependencies>
#
# Licence: GPL v3

# Installation instructions: 
# -------------------------- 
# Execute in terminal.app before running : 
#    sudo easy_install keyring
#
# Ensure you have bitbar installed https://github.com/matryer/bitbar/releases/latest
# Ensure your bitbar plugins directory does not have a space in the path (known bitbar bug)
# Copy this file to your bitbar plugins folder and chmod +x the file from your terminal in that folder
# Run bitbar

_DEBUG_ = False 

try:   # Python 3 dependencies
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen, build_opener
    from urllib.request import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler, HTTPError, URLError
except: # Python 2 dependencies
    from urllib import urlencode
    from urllib2 import Request, urlopen, build_opener
    from urllib2 import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler, HTTPError, URLError


import ast
import json
import sys
import datetime
import calendar
import base64
import math
import keyring                                  # Cowboy access token is stored in OS X keychain
import getpass                                  # Getting password without showing chars in terminal.app
import time
import os
import subprocess
import requests
import binascii

from datetime   import date
from tinydb     import TinyDB                   # Keep track of location and cowboy states
from os.path    import expanduser

from collections import OrderedDict

import library.snf as sonoff


# Location where to store state files
home         = expanduser("~")
state_dir    = home+'/.state/mysonoff'

if not os.path.exists(state_dir):
    os.makedirs(state_dir)


# Nice ANSI colors
CEND    = '\33[0m'
CRED    = '\33[31m'
CGREEN  = '\33[32m'
CYELLOW = '\33[33m'
CBLUE   = '\33[34m'

# Support for OS X Dark Mode
DARK_MODE=os.getenv('BitBarDarkMode',0)

# Pretty printing                                                               
                                                                                
def justify(string):                                                            
    return justify(string,10)                                                   
                                                                                
def justify(string,number):                                                     
    length = len(string)                                                        
    quot   = (number - length ) // 4                                            
    rem    = (number - length )  % 4                                            
    return string.ljust(length+rem,' ').ljust(length+rem+quot,'\t')   


# Logo for both dark mode and regular mode
def app_print_logo():
   if bool(DARK_MODE):
      print ('|image=iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAAAXNSR0IArs4c6QAAAIRlWElmTU0AKgAAAAgABQESAAMAAAABAAEAAAEaAAUAAAABAAAASgEbAAUAAAABAAAAUgEoAAMAAAABAAIAAIdpAAQAAAABAAAAWgAAAAAAAACQAAAAAQAAAJAAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAACSgAwAEAAAAAQAAACQAAAAAODYCaQAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAVlpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDUuNC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KTMInWQAAA11JREFUWAndmD1oFFEQx73EKH4SkICdiKWVdhqJFiKkEEsRe1uxskgtFhZqoVhZCdqLRQpRA0IQO1Ek2FkoiBoQEc0l5++3twN7l739eAQDDvxv5r353Hlzu3vX2VJCvV5vrNPprMF3oJ4GE6BXYtpmq4PxCnhJ7F+RozaAhhrBp8AHsNFkzKk8R5arWNTW4iKXx+Fr4BI4BE6Cz2A7cD+FTPwb7AcvgLGvgciF2KeygkK3D2GZ9i7ExgbwJbqzTBxjl1JVQat4TBBAG+Vor7PkPDShoq3dtSPOo/FKqaogkxpwlS42R2s5N6j7oor0x6Wziq/cGBZSLHKdf1VBA8Z5QAOPvLoBh7zgKGZIN3LZuCACj1sMfIZoN8EeMKpLducHuILPQviyrqXGBREp5uY68hHwEOwCw0Vp9xNcANp6HwtfxGpqU1AktojHXPnFqtB0ZTf6A7lN+Fa5ZLo2BUUwg+90QVLvTcMz5dF6z9GmcSHYZpRSkI6RqOtc9UP1PykydMGL6lo57i21hv/K4L8rqOzbU7bXuMGpMxRJxxgZ79xFiq6HTVFXK6cUZKI/RmagMz6UJYZcXeuiUgryDnyazjyDd4Ex/PpLft1j7zjyKzfbULS3jY+2+vn2dwwcBBYhlN1TlxQ7xWkvyeY5rjPwJXAHeUYou5fr5pG1bUUpR2YnJvMs5+DLHF8kvsf6Ua7TRttWlNKh72SYpoizdOIjcKYeCGX31GkDtG1FKR2yG2/Bk0KmuYKsqE6b6Jx7jSilQ9uIbGf8mfQazCG/EcruqdMGaNuKUjpkgnhw3kV+V8j4FPlTvg6bgrpeTCnIuZilEyfoxH1TIN+Ws74MW1QHnwXPQStKKchfDd+AMxK0GELO1WmjbStqU1A8Bnx2+RP7Bp2Ygns02beJ9Xlk7b4AbeI5F75sVVObgmImrhLyFjgFvM+YLBL7HNPuMHgPtJXCt7+q+GxcEPMRv68WiHe0IuaAiq7hOvhWOWAwtGhcUB4Ylr1ueMV1V23nsmLCdyh36bKqIBNmx0FAj8J3H4PEfpO5wKX/vgT33uTR6jfyYqoK0nmFS4znUbznsJ1MXQrzTSBmbl2gqoK+Yj1JAJ/iG/l3jA9dYzcjCsgeJ/BN+cOqdA4siqPalL/0/gKkeO/loYY4BQAAAABJRU5ErkJggg==')
   else:
      print ('|image=iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAAAAXNSR0IArs4c6QAAAIRlWElmTU0AKgAAAAgABQESAAMAAAABAAEAAAEaAAUAAAABAAAASgEbAAUAAAABAAAAUgEoAAMAAAABAAIAAIdpAAQAAAABAAAAWgAAAAAAAACQAAAAAQAAAJAAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAACSgAwAEAAAAAQAAACQAAAAAODYCaQAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAVlpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDUuNC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KTMInWQAAAzFJREFUWAndmDtoFUEUhhPjA58IErATsbTSTiPRQgQLsRSxtxUrC2uxsFALxcpK0F4sLEQTCIjYiSIhnYWC+AAR0fj6Pu8eXTd7Z3cmFwsP/HfOzvznnP+enZ29yfhYu61g+jtYC6bAKvADLMfGCV4Ec+ATiBq4aZOoTYIFoJBRwpzm1qLW4IrPlb+9P84Ert05CXaA/eAVWAOcLzELfwZbwQww9zkQtXAH1iYo1rbgvAezMTGCcb7Kae5WSwn6RoR7R42+tNfb537oY3Wu3bUj5jRfq6UEWdSEBjua0NGkjiJlxgvjm7m8brWUoGaAAqJAc63tOgSHmDbOkrkcQXbGbzsNLoKNIIri/mWK+ABOA/dgxOKmLUdQtPk8KXeBm2A9aIqS9xEcB3I9xyIWN205gqKwIm6DE+nUYxtY31ZxIrYjpP0c6goy+bqK5NnUfGK8PZ42cnoLgfvLcjoUMY5R6Ct+U1CsxViP6/TjbOkk/ivCfyeo7elpm+vd4NI9FEXtsJu4btH14NTXOv0SQRb6UmWOsV4oNrlr2aJKBHkCHwT3gU+ZOXz8NR/3mNuL/8jJHIv25sTINc5ff3vAdqAIoe+ca0W5S4I2UewuOATmwRXg+03oO+eaHLlZVnLL7MTmqspRRn/EReFr+LeqNTlys6ykQ++o4AvzCHgB3FM3Kug755ocuVlW0iG78RTcqVU6W/N1XZMTnXOul5V0aDWZ7YK/IB8DxTypoO+ca3LkZllJhywQL86r+M9qFe/hv6yug1Nb7nZLBLkvDoN94HpV4nI1nmJ8CFyT8wBkWYkg/2p4C9wjYYqom2ty5GZZjqB4DUxQwT+xL4BJ4K2Jp+kYvrzXQI5cLWIHV4nPHEGxJ86Q7xI4ADxnLBaFfY/J2wmeA7laxA6uEp85gixm8VmwO5GzuWRMvHCba0uucwSZ2G9qNxy7vrX8EBOxTKUtJciCJlKA3zDOrJh3rcvkxu30bNJPiksJMngRxPuod9uJGWbmMmeIXMJLCXoD2xfkNBjlv2PMae7eFrfGR3oB2PZRwpzm1qLW4IrPYftAovfcs2QKeMApajlmLW/XHBj6L72fdknNe6HtIn8AAAAASUVORK5CYII=')
   print('---')


# --------------------------
# The main function
# --------------------------

# The init function: Called to store your username and access_code in OS X Keychain on first launch
def init():
    # Here we do the setup
    # Store access_token in OS X keychain on first run
    print ('Enter your Sonoff username:')
    init_username = raw_input()
    print ('Enter your Sonoff password:')
    init_password = getpass.getpass()
    init_access_token = None

    try:
        c = sonoff.Sonoff(init_username,init_password,'eu')
    except HTTPError as e:
        print ('Error contacting Sonoff servers. Try again later.')
        print e
        time.sleep(0.5)
        return
    except URLError as e:
        print ('Error: Unable to connect. Check your connection settings.')
        print e
        return
    except AttributeError as e:
        print ('Error: Could not get an access token from Sonoff. Try again later.')
        print e
        return
    keyring.set_password("mysonoff-bitbar","username",init_username)
    keyring.set_password("mysonoff-bitbar","password",init_password)
    init_password = ''



USERNAME = keyring.get_password("mysonoff-bitbar","username")  



# --------------------------
# The main function
# --------------------------

def main(argv):

    # CASE 1: init was called 
    if 'init' in argv:
       init()
       return
  

    # CASE 2: init was not called, keyring not initialized
    if bool(DARK_MODE):
        color = '#FFDEDEDE'
        info_color = '#808080'
    else:
        color = 'black' 
        info_color = '#808080'

    if not USERNAME:   
       # restart in terminal calling init 
       app_print_logo()
       print ('Login to Sonoff | refresh=true terminal=true bash="\'%s\'" param1="%s" color=%s' % (sys.argv[0], 'init', color))
       return


    # CASE 3: init was not called, keyring initialized, no connection (access code not valid)
    try:
       True
       # create connection to cowboy account
       PASSWORD = keyring.get_password("mysonoff-bitbar","password")
       c = sonoff.Sonoff(USERNAME,PASSWORD,'eu')
       devices = c.get_devices()
    except: 
       app_print_logo()
       print ('Login to Sonoff | refresh=true terminal=true bash="\'%s\'" param1="%s" color=%s' % (sys.argv[0], 'init', color))
       return


    # CASE 4: all ok, specific command for a specific switch received
    if (len(argv) > 1) and not('debug' in argv):

        if (argv[1] == "switch"):
           if (len(argv) == 4): 
              c.switch(argv[3],argv[2],None)
           elif (len(argv) == 5):
              c.switch(argv[3],argv[2],int(argv[4]))
           else:
              print ('Wrong number of arguments: switch <id> <state:on/off> <optional:outlet>')
              return
        return


    # CASE 5: all ok, all other cases
    app_print_logo()
    prefix = ''

    # --------------------------------------------------
    # DEBUG MENU
    # --------------------------------------------------

    if 'debug' in argv:
        for i in devices:
            print ('>>> device: %s - %s' % (i['name'], i['params']['switch']))
        return


    # --------------------------------------------------
    # MENU 
    # --------------------------------------------------

    devices_ordered = sorted(devices, key= lambda(i) : i['name'])

    for i in devices_ordered:
 
       outlets = i['uiid']
       devid   = i['deviceid']
       name    = i['name']

       try:
           if i['params']['switches']: # Multiple outlets on 1 switch
              for d, j in enumerate(i['params']['switches']):
                  state = j['switch']
                  if (d < outlets): 
                     outletnbr  = d+1
                     outletname = name + ' (outlet ' + str(outletnbr) + ')\t\t'
                     if (state == 'on'):
                        print ('%s%s %s%s%s | refresh=true terminal=false bash="%s" param1=%s param2=%s param3=%s param4=%s color=%s' % (prefix, justify(outletname,42), CGREEN, state, CEND, sys.argv[0], 'switch', devid, 'off', d, color))
                        print ('%s%s %s%s%s | refresh=true alternate=true terminal=true bash="%s" param1=%s param2=%s param3=%s param4=%s color=%s' % (prefix, justify(outletname,42), CGREEN, state, CEND, sys.argv[0], 'switch', devid, 'off', d, color))
                     else:
                        print ('%s%s %s%s%s | refresh=true terminal=false bash="%s" param1=%s param2=%s param3=%s param4=%s color=%s' % (prefix, justify(outletname,42), CRED, state, CEND, sys.argv[0],  'switch', devid, 'on', d, color))
                        print ('%s%s %s%s%s | refresh=true alternate=true terminal=true bash="%s" param1=%s param2=%s param3=%s param4=%s color=%s' % (prefix, justify(outletname,42), CRED, state, CEND, sys.argv[0], 'switch', devid, 'on', d, color))
       except:             # Just one switch 
          state = i['params']['switch']
          if (state == 'on'):
             print ('%s%s %s%s%s | refresh=true terminal=false bash="%s" param1=%s param2=%s param3=%s color=%s' % (prefix, justify(name,42), CGREEN, state, CEND, sys.argv[0], 'switch', devid, 'off', color))
             print ('%s%s %s%s%s | refresh=true alternate=true terminal=true bash="%s" param1=%s param2=%s param3=%s color=%s' % (prefix, justify(name,42), CGREEN, state, CEND, sys.argv[0], 'switch', devid, 'off', color))
          else:
             print ('%s%s %s%s%s | refresh=true terminal=false bash="%s" param1=%s param2=%s param3=%s color=%s' % (prefix, justify(name,42), CRED, state, CEND, sys.argv[0],  'switch', devid, 'on', color))
             print ('%s%s %s%s%s | refresh=true alternate=true terminal=true bash="%s" param1=%s param2=%s param3=%s color=%s' % (prefix, justify(name,42), CRED, state, CEND, sys.argv[0], 'switch', devid, 'on', color))
 



if __name__ == '__main__':
    main(sys.argv)
