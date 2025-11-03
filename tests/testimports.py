import sys
from subprocess import check_output
from textwrap import dedent


def test_no_blocklist_imports():
    # setuptools_scm is imported when importing param. It itself imports
    # the logging module.
    blocklist = {"numpy", "IPython", "pandas", "asyncio", "html", "logging"}
    try:
        import setuptools_scm  # noqa
        blocklist.remove("logging")
    except ModuleNotFoundError:
        pass

    check = f"""\
    import sys
    sys.modules.pop("logging", None)  # Added because of coverage will add it
    import param

    blocklist = {blocklist}
    mods = blocklist & set(sys.modules)

    if mods:
        print(", ".join(mods), end="")
    """

    output = check_output([sys.executable, '-c', dedent(check)])

    assert output == b""
