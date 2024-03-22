import asyncio
import logging
import time

from contextlib import contextmanager

import param


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs.

    Messages are available from an instance's ``messages`` dict, in
    order, indexed by a lowercase log level string (e.g., 'debug',
    'info', etc.).

    This is typically used by using a setUpClass classmethod and a setUp
    method on a test case. The setUpClass classmethod can be configured
    as follows after calling super (with cls):

    log = param.parameterized.get_logger()
    cls.log_handler = MockLoggingHandler(level='DEBUG')
    log.addHandler(cls.log_handler)

    The setUp method then just needs to call self.log_handler.reset()
    between tests (typically after invoking super). This is necessary to
    make the tests independent where the tests can use the
    self.log_handler.tail and self.log_handler.assertEndsWith methods.
    """

    def __init__(self, *args, **kwargs):
        self.messages = {'DEBUG': [], 'INFO': [], 'WARNING': [],
                         'ERROR': [], 'CRITICAL': [], 'VERBOSE':[]}
        super().__init__(*args, **kwargs)

    def emit(self, record):
        "Store a message to the instance's messages dictionary"
        self.acquire()
        try:
            self.messages[record.levelname].append(record.getMessage())
        finally:
            self.release()

    def reset(self):
        self.acquire()
        self.messages = {'DEBUG': [], 'INFO': [], 'WARNING': [],
                         'ERROR': [], 'CRITICAL': [], 'VERBOSE':[]}
        self.release()

    def tail(self, level, n=1):
        "Returns the last n lines captured at the given level"
        return [str(el) for el in self.messages[level][-n:]]

    def assertEndsWith(self, level, substring):
        """
        Assert that the last line captured at the given level ends with
        a particular substring.
        """
        msg='\n\nparam.log({level},...): {last_line}\ndoes not end with:\n{substring}'
        last_line = self.tail(level, n=1)
        if len(last_line) == 0:
            raise AssertionError('Missing param.log({level},...) output: {substring}'.format(
                level=level, substring=repr(substring)))
        if not last_line[0].endswith(substring):
            raise AssertionError(msg.format(level=level,
                                            last_line=repr(last_line[0]),
                                            substring=repr(substring)))

    def assertContains(self, level, substring):
        """
        Assert that the last line captured at the given level contains a
        particular substring.
        """
        msg='\n\nparam.log({level},...): {last_line}\ndoes not contain:\n{substring}'
        last_line = self.tail(level, n=1)
        if len(last_line) == 0:
            raise AssertionError('Missing output: {substring}'.format(
                substring=repr(substring)))
        if substring not in last_line[0]:
            raise AssertionError(msg.format(level=level,
                                            last_line=repr(last_line[0]),
                                            substring=repr(substring)))


def check_defaults(parameter, label, skip=[]):
    # ! Not testing default and allow_None
    if 'doc' not in skip:
        assert parameter.doc is None
    if 'precedence' not in skip:
        assert parameter.precedence is None
    if 'instantiate' not in skip:
        assert parameter.instantiate is False
    if 'constant' not in skip:
        assert parameter.constant is False
    if 'readonly' not in skip:
        assert parameter.readonly is False
    if 'pickle_default_value' not in skip:
        assert parameter.pickle_default_value is True
    if 'per_instance' not in skip:
        assert parameter.per_instance is True
    if 'label' not in skip:
        assert parameter.label == label


@contextmanager
def warnings_as_excepts(match=None):
    orig = param.parameterized.warnings_as_exceptions
    param.parameterized.warnings_as_exceptions = True
    try:
        yield
    except Exception as e:
        if match and match not in str(e):
            raise ValueError(f'Exception emitted {str(e)!r} does not contain {match!r}')
    finally:
        param.parameterized.warnings_as_exceptions = orig


async def async_wait_until(fn, timeout=5000, interval=100):
    """
    Exercise a test function in a loop until it evaluates to True
    or times out.

    The function can either be a simple lambda that returns True or False:
    >>> await async_wait_until(lambda: x.values() == ['x'])

    Or a defined function with an assert:
    >>> async def _()
    >>>    assert x.values() == ['x']
    >>> await async_wait_until(_)

    Parameters
    ----------
    fn : callable
        Callback
    timeout : int, optional
        Total timeout in milliseconds, by default 5000
    interval : int, optional
        Waiting interval, by default 100

    Adapted from pytest-qt.
    """
    # Hide this function traceback from the pytest output if the test fails
    __tracebackhide__ = True

    start = time.monotonic()

    def timed_out():
        elapsed = time.monotonic() - start
        elapsed_ms = elapsed * 1000
        return elapsed_ms > timeout

    timeout_msg = f"async_wait_until timed out in {timeout} milliseconds"

    while True:
        try:
            result = fn()
            if asyncio.iscoroutine(result):
                result = await result
        except AssertionError as e:
            if timed_out():
                raise TimeoutError(timeout_msg) from e
        else:
            if result not in (None, True, False):
                raise ValueError(
                    "`async_wait_until` callback must return None, True, or "
                    f"False, returned {result!r}"
                )
            # None is returned when the function has an assert
            if result is None:
                return
            # When the function returns True or False
            if result:
                return
            if timed_out():
                raise TimeoutError(timeout_msg)
        await asyncio.sleep(interval / 1000)
