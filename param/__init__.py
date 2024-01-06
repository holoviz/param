# adapted from param holoviz - https://github.com/holoviz/param - see following license
"""
Copyright (c) 2005-2022, HoloViz team.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the
   distribution.

 * Neither the name of the copyright holder nor the names of any
   contributors may be used to endorse or promote products derived
   from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import print_function

"""
Parameters are a kind of class attribute allowing special behavior,
including dynamically generated parameter values, documentation
strings, constant and read-only parameters, and type or range checking
at assignment time.

Potentially useful for any large Python program that needs
user-modifiable object attributes; see the Parameter and Parameterized
classes for more information.  If you do not want to add a dependency
on external code by importing from a separately installed param
package, you can simply save this file as param.py and copy it and
parameterized.py directly into your own package.

This file contains subclasses of Parameter, implementing specific
parameter types (e.g. Number), and also imports the definition of
Parameters and Parameterized classes.
"""
from . import exceptions
from .parameterized import (Parameterized, ParameterizedFunction, ParamOverrides, Parameter,
    depends_on, instance_descriptor, discard_events, edit_constant, )

from .logger import get_logger, logging_level, VERBOSE

# Determine up-to-date version information, if possible, but with a
# safe fallback to ensure that this file and parameterized.py are the
# only two required files.
try:
    from .version import Version
    __version__ = str(Version(fpath=__file__, archive_commit="$Format:%h$", reponame="param"))
except:
    __version__ = "0.0.0+unknown"

