# -*- coding: utf-8 -*-
# authomatic providers config.py
## WARNING : this class is empty and showcases the app/auth/auth_config.py that is required to run backend locally.
## Please use your own consumer and secret keys.

import authomatic
from authomatic.providers import oauth1, oauth2

CONFIG = { 
    'twitter': {  # Your internal provider name
        # Provider class
        'class_': oauth1.Twitter,
        'consumer_key': '####',
        'consumer_secret': '####',
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
        'consumer_key': '###',
        'consumer_secret': '###',
        'id': authomatic.provider_id(),
        'scope': oauth2.Facebook.user_info_scope
    },

    'google': {
        'class_': oauth2.Google,
        'consumer_key': '###',
        'consumer_secret': '###',
        'id': authomatic.provider_id(),
        'scope': oauth2.Google.user_info_scope
    },

    'github': {

        'class_': oauth2.GitHub,
        'consumer_key':'###',
        'consumer_secret': '###',
        'id': authomatic.provider_id(),
        'scope': oauth2.GitHub.user_info_scope
    },

    'linkedin': {
        'class_': oauth2.LinkedIn,
        'consumer_key': '###',
        'consumer_secret': '###',
        'id': authomatic.provider_id(),
        'scope': oauth2.LinkedIn.user_info_scope,
        '_name': 'LinkedIn',
    },
}
