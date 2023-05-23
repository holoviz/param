# -*- coding: utf-8 -*-

import param

param.parameterized.docstring_signature = False
param.parameterized.docstring_describe_params = False

from nbsite.shared_conf import *  # noqa

project = u'param'
authors = u'HoloViz developers'
copyright = u'2003-2022 ' + authors
description = 'Declarative Python programming using Parameters'

version = release = base_version(param.__version__)  # noqa

nbbuild_cell_timeout = 600

html_static_path += ['_static']  # noqa

html_logo = "_static/logo_horizontal.png"

html_favicon = "_static/favicon.ico"

html_css_files = [
    'nbsite.css',
    'scroller.css',
    'notebook.css',
]

exclude_patterns += ['historical_release_notes.rst']  # noqa

html_theme_options = {
    "github_url": "https://github.com/holoviz/param",
    "icon_links": [
        {
            'name': 'Twitter',
            'url': 'https://twitter.com/holoviz_org',
            'icon': 'fa-brands fa-twitter-square',
        },
        {
            "name": "Discourse",
            "url": "https://discourse.holoviz.org/",
            "icon": "fa-brands fa-discourse",
        },
        {
            "name": "Discord",
            "url": "https://discord.gg/AXRHnJU6sP",
            "icon": "fa-brands fa-discord",
        },
    ],
    "footer_items": [
        "copyright",
        "last-updated",
    ],
    "analytics": {"google_analytics_id": 'UA-154795830-6'},
}

# Override the Sphinx default title that appends `documentation`
html_title = f'{project} v{version}'
# Format of the last updated section in the footer
html_last_updated_fmt = '%Y-%m-%d'
