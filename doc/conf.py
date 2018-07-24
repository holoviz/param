# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

project = u'Param'
authors = u'PyViz authors'
copyright = u'\u00a9 2005-2018, ' + authors
description = 'Declarative Python programming using Parameters.'

import param
version = release = param.__version__

html_static_path += ['_static']
html_theme = 'sphinx_ioam_theme'
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
    # will work without this - for canonical (so can ignore when building locally or test deploying)    
    'WEBSITE_SERVER': 'https://param.pyviz.org',
    'VERSION': version,
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Gitter', '//gitter.im/ioam/holoviews'),
        ('Github', '//github.com/ioam/param'),
    )
})
