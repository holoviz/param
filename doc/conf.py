# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

project = u'Param'
authors = u'HoloViz authors'
copyright = u'\u00a9 2005-2018, ' + authors
description = 'Declarative Python programming using Parameters.'

import param
version = release = param.__version__

html_static_path += ['_static']
html_theme = 'sphinx_holoviz_theme'
html_theme_options = {
    'logo':'logo.png',
    'favicon':'favicon.ico',
#    'css':'site.css'
}

_NAV =  (
    ('API', 'Reference_Manual/param'),
    ('About', 'About'),
)

html_context.update({
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    # canonical URL (for search engines); can ignore for local builds
    'WEBSITE_SERVER': 'https://param.holoviz.org',
    'VERSION': version,
    'GOOGLE_ANALYTICS_UA': 'UA-154795830-6',
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Gitter', '//gitter.im/pyviz/pyviz'),
        ('Github', '//github.com/ioam/param'),
    )
})
