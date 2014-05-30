# -*- coding: utf-8 -*-

from builder.shared_conf import *  # pyflakes:ignore (API import)

paths = ['.', '..']
add_paths(paths)

# General information about the project.
project = u'Param'
copyright = u'2014, IOAM'
ioam_project = 'param'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.1'
# The full version, including alpha/beta/rc tags.
release = '1.1-devel'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static', 'builder/_shared_static']

# Output file base name for HTML help builder.
htmlhelp_basename = project + 'doc'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', project+'.tex', project + ' Documentation',
   u'IOAM', 'manual'),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', ioam_project, project + ' Documentation',
     [u'IOAM'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', project, project + ' Documentation',
   u'IOAM', project, 'One line description of project.',
   'Miscellaneous'),
]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}
