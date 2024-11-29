import logging
import time
from functools import wraps
from flask import request
from flask_login import current_user

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s : %(message)s',
)

logger = logging.getLogger("arborator_app")


def log_request(func):
    @wraps(func)
    def log_wrapper(*args, **kwargs):
        begin = time.time()
        
        logger.info('Request method {}'.format(request.method))
        logger.info('Request path {}'.format(request.path))
        if current_user.is_authenticated:
            logger.info('Request done by {}'.format(current_user.id))
        else:
            logger.info('Request done by anonymous user')
            
        response = func(*args, **kwargs)
        
        end = time.time()
        execution_time = (end - begin)
        logger.info('Execution time {} s'.format(execution_time))
        logger.info('Response status {}'.format(response[1]))
        
        return response
    
    return log_wrapper

        