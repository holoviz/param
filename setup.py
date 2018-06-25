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
        'nose',
        'flake8',
    ]
}

extras_require['all'] = sorted(set(sum(extras_require.values(), [])))


########## metadata for setuptools ##########

setup_args = dict(
    name='param',
    version=get_setup_version("param"),
    description='Declarative Python programming using Parameters.',
    long_description=open('README.rst').read() if os.path.isfile('README.rst') else 'Consult README.rst',
    author="IOAM",
    author_email="developers@topographica.org",
    maintainer="IOAM",
    maintainer_email="developers@topographica.org",
    platforms=['Windows', 'Mac OS X', 'Linux'],
    license='BSD',
    url='http://ioam.github.com/param/',
    packages=["param","numbergen"],
    provides=["param","numbergen"],
    include_package_data = True,
    python_requires=">=2.7",
    install_requires=[],
    extras_require=extras_require,
    tests_require=extras_require['tests'],
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries"]
)


if __name__=="__main__":
    setup(**setup_args)
