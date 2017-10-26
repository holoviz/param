import sys
import unittest

if sys.version_info <= (2,6):
    del sys.modules['unittest']
    sys.modules['unittest'] = __import__('unittest2')
