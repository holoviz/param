# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

project = u'param'
authors = u'HoloViz developers'
copyright = u'2003-2020 ' + authors
description = 'Declarative Python programming using Parameters'

import param
version = release = str(param.__version__)

param.parameterized.docstring_signature = False
param.parameterized.docstring_describe_params = False

nbbuild_cell_timeout = 600

html_static_path += ['_static']
html_theme = 'sphinx_holoviz_theme'
html_theme_options = {
    'favicon': 'favicon.ico',
    'logo': 'logo_horizontal_white.svg',
    'include_logo_text': False,
    'primary_color': '#266498',
    'primary_color_dark': '#1b486e',
    'secondary_color': '#5f9df0',
#    'css':'site.css'
    'second_nav': True,
    'footer': False,
}

_NAV =  (
    ('Getting Started', 'getting_started'),
    ('User Guide', 'user_guide/index'),
    ('API', 'Reference_Manual/index'),
    ('About', 'about')
)

html_context.update({
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    'VERSION': version,
    'GOOGLE_ANALYTICS_UA': 'UA-154795830-6',
    'WEBSITE_URL': 'https://param.holoviz.org',
    'WEBSITE_SERVER': 'https://param.holoviz.org',
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Discourse', '//discourse.holoviz.org'),
        ('Github', '//github.com/holoviz/param'),
    )
})
