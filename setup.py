import os

from setuptools import setup


########## autover ##########

def get_setup_version(reponame):
    """Use autover to get up to date version."""
    # importing self into setup.py is unorthodox, but param has no
    # required dependencies outside of python
    from param.version import Version
    return Version.setup_version(os.path.dirname(__file__),reponame,archive_commit="$Format:%h$")


########## dependencies ##########

extras_require = {
    # pip doesn't support tests_require
    # (https://github.com/pypa/pip/issues/1197)
    'tests': [
        'pytest',
        'pytest-cov',
        'flake8',
    ],
    'doc': [
        'pygraphviz',
        'nbsite >=0.6.1',
        'pydata-sphinx-theme',
        'myst-parser',
        'nbconvert <6.0',
        'graphviz',
        'myst_nb ==0.12.2',
        'aiohttp',
        'panel',
    ]
}

extras_require['all'] = sorted(set(sum(extras_require.values(), [])))


########## metadata for setuptools ##########

setup_args = dict(
    name='param',
    version=get_setup_version("param"),
    description='Make your Python code clearer and more reliable by declaring Parameters.',
    long_description=open('README.md').read() if os.path.isfile('README.md') else 'Consult README.md',
    long_description_content_type="text/markdown",
    author="HoloViz",
    author_email="developers@holoviz.org",
    maintainer="HoloViz",
    maintainer_email="developers@holoviz.org",
    platforms=['Windows', 'Mac OS X', 'Linux'],
    license='BSD',
    url='http://param.holoviz.org/',
    packages=["param","numbergen"],
    provides=["param","numbergen"],
    include_package_data = True,
    python_requires=">=2.7",
    install_requires=[],
    extras_require=extras_require,
    tests_require=extras_require['tests'],
    project_urls={
        "Documentation": "https://param.holoviz.org/",
        "Releases": "https://github.com/holoviz/param/releases",
        "Bug Tracker": "https://github.com/holoviz/param/issues",
        "Source Code": "https://github.com/holoviz/param",
        "Panel Examples": "https://panel.holoviz.org/user_guide/Param.html",
    },
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries"]
)


if __name__=="__main__":
    setup(**setup_args)
