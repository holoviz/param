import sys
from subprocess import check_output
from textwrap import dedent


def test_no_blocklist_imports():
    check = """\
    import sys
    import param

    blocklist = {"numpy", "IPython", "pandas"}
    mods = blocklist & set(sys.modules)

    if mods:
        print(", ".join(mods), end="")
    """

    output = check_output([sys.executable, '-c', dedent(check)])

    assert output == b""
