import sys
import unittest

if sys.version_info[0]==2 and sys.version_info[1]<7:
    del sys.modules['unittest']
    sys.modules['unittest'] = __import__('unittest2')
