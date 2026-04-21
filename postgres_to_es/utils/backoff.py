import random
import time
from functools import wraps


def backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10, ):
    """Реализация техники backoff"""
    def func_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            n = 0
            t = start_sleep_time
            while True:
                try:
                    return func(*args, **kwargs)
                except:
                    sleep_time = min(t, border_sleep_time)

                    sleep_time = random.uniform(0, sleep_time)

                    time.sleep(sleep_time)

                    n += 1
                    t = start_sleep_time * (factor ** n)

        return inner

    return func_wrapper
