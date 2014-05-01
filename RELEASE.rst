How to make a new release of ``param``
======================================

- [Insert important tasks such as review commit log, update release
  notes, etc!]

- Add the version number as a tag in git::

   git tag -a 1.0.0 -m "Creating first official version."

- Push the tag to github::

   git push --tags origin master

- Publish on PyPi::

   python setup.py sdist upload

- [Insert important tasks such as update webpage...]
