# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

project = u'param'
authors = u'HoloViz developers'
copyright = u'2003-2022 ' + authors
description = 'Declarative Python programming using Parameters'

import param

param.parameterized.docstring_signature = False
param.parameterized.docstring_describe_params = False

version = release = base_version(param.__version__)

nbbuild_cell_timeout = 600

html_static_path += ['_static']

html_theme = "pydata_sphinx_theme"

html_logo = "_static/logo_horizontal.png"

html_favicon = "_static/favicon.ico"

html_css_files = ['site.css']

exclude_patterns += ['historical_release_notes.rst']

html_theme_options = {
    "github_url": "https://github.com/holoviz/param",
    "icon_links": [
        {
            'name': 'Twitter',
            'url': 'https://twitter.com/holoviz_org',
            'icon': 'fab fa-twitter-square',
        },
        {
            "name": "Discourse",
            "url": "https://discourse.holoviz.org/",
            "icon": "fab fa-discourse",
        },
    ],
    "footer_items": [
        "copyright",
        "last-updated",
    ],
    'google_analytics_id': 'UA-154795830-6',
}

extensions += ['sphinx_copybutton']

# Override the Sphinx default title that appends `documentation`
html_title = f'{project} v{version}'
# Format of the last updated section in the footer
html_last_updated_fmt = '%Y-%m-%d'
