# -*- coding: utf-8 -*-
# authomatic providers config.py

import authomatic
from authomatic.providers import oauth1, oauth2

from flask import current_app

CONFIG = { 
    'twitter': {  # Your internal provider name
        # Provider class
        'class_': oauth1.Twitter,
        'consumer_key': 'Sd6hNLuOnTWM428Q2tObxIeyD',
        'consumer_secret': 'VBk11n5sdMNkUNs49SEcenSUdr86jCXoYplF8nqqwPCXCg398q',
        'id': authomatic.provider_id()
    },

    # 'yahoo': {
    #     'class_': oauth1.Yahoo,
    #     'consumer_key': '##########--',
    #     'consumer_secret': '##########',
    #     'id': authomatic.provider_id()
    # },

    'facebook': {

        'class_': oauth2.Facebook,
        'consumer_key': '586660258357828',
        'consumer_secret': 'ccd636977a6ccc08468950a04a2af812',
        'id': authomatic.provider_id(),
        'scope': oauth2.Facebook.user_info_scope
    },

    'google': {
        'class_': oauth2.Google,
        'consumer_key': '890198703708-7pn39h2nghq2l87s8psg7seaertta7k5.apps.googleusercontent.com',
        'consumer_secret': '47GparxWHFfB5GUzvA_X880t',
        'id': authomatic.provider_id(),
        'scope': oauth2.Google.user_info_scope
    },

    'github': {

        # prod
        'consumer_key':'a10dffc2b29dbddacb9d',
        'consumer_secret': '59cf1a4ffda3d036bc8274131ad82e7fa6038c01',

        # dev
        #'consumer_key':'924aedede12fde87b5f4',
        #'consumer_secret':'4b4e6235887137665573659c7ebd2f3980dde718',

        # shared
        'class_': oauth2.GitHub,
        'id': authomatic.provider_id(),
        'scope': oauth2.GitHub.user_info_scope
    },

    'linkedin': {
        'class_': oauth2.LinkedIn,
        'consumer_key': '86z1ib5ntkq6io',
        'consumer_secret': '0kLc3ZYeEo4RxiLl',
        'id': authomatic.provider_id(),
        'scope': oauth2.LinkedIn.user_info_scope,
        '_name': 'LinkedIn',
    },
}
