import logging

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
        super(MockLoggingHandler, self).__init__(*args, **kwargs)

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
            raise AssertionError('Missing {method} output: {substring}'.format(
                level=level, substring=repr(substring)))
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
