import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

try:
    import param
    version = param.__version__
except ImportError:
    version = '1.5.1'

install_requires = []
if sys.version_info[0]==2 and sys.version_info[1]<7:
    install_requires+=['ordereddict','unittest2']


setup_args = dict(
    name='param',
    version=version,
    description='Declarative Python programming using Parameters.',
    long_description=open('README.rst').read() if os.path.isfile('README.rst') else 'Consult README.rst',
    author= "IOAM",
    author_email= "developers@topographica.org",
    maintainer="IOAM",
    maintainer_email="developers@topographica.org",
    platforms=['Windows', 'Mac OS X', 'Linux'],
    license='BSD',
    url='http://ioam.github.com/param/',
    packages = ["param","numbergen"],
    provides = ["param","numbergen"],
    install_requires = install_requires,
    classifiers = [
        "License :: OSI Approved :: BSD License",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
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


def _making_dist():
    for arg in sys.argv:
        # (note: not supposed to use 'upload' now)
        if 'dist' in arg or arg == 'upload':
            return True
    return False


if __name__=="__main__":

    # get a meaningful version in dists built between official releases
    if os.environ.get('PARAM_MAKING_UNOFFICIAL_RELEASE') == '1':
        if _making_dist():
            try:
                import param
                setup_args['version'] = param.__version__
                with open('param/_version.py','w') as f:
                    f.write('commit_count=%s\ncommit="%s"\n'%(param.__version__.commit_count,
                                                              param.__version__.commit))
            except ImportError:
                pass

    if _making_dist():
        import param, numbergen
        param.__version__.verify(setup_args['version'])
        numbergen.__version__.verify(setup_args['version'])

    setup(**setup_args)
