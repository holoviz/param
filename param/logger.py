import logging
from contextlib import contextmanager
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL, Logger



VERBOSE = INFO - 1
logging.addLevelName(VERBOSE, "VERBOSE")
    
def get_logger(name : str = None) -> Logger:
    if name is None:
        root_logger = logging.getLogger('param')
        if not root_logger.handlers:
            root_logger.setLevel(logging.INFO)
            formatter = logging.Formatter(
                fmt='%(levelname)s:%(name)s: %(message)s')
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
            return root_logger
    else:
        return logging.getLogger('param.' + name)


@contextmanager
def logging_level(level : int):
    """
    Temporarily modify param's logging level.
    """
    level = level.upper()
    levels = [DEBUG, INFO, WARNING, ERROR, CRITICAL, VERBOSE]
    level_names = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'VERBOSE']

    if level not in level_names:
        raise Exception("Level %r not in %r" % (level, levels))

    param_logger = get_logger()
    logging_level = param_logger.getEffectiveLevel()
    param_logger.setLevel(levels[level_names.index(level)])
    try:
        yield None
    finally:
        param_logger.setLevel(logging_level)



__all__ = ['logging_level', 'get_logger']