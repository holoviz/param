# Developer Guide

Welcome. We are so happy you've decided to contribute.

## Setting up a development environment

This guide describes how to install and configure development environments.

If you have any problems with the steps here, please reach out in the `dev` channel on [Discord](https://discord.gg/rb6gPXbdAr) or on [Discourse](https://discourse.holoviz.org/).

## Preliminaries

### Basic understanding of how to contribute to Open Source

If this is your first open-source contribution, please study one or more of the below resources.

- [How to Get Started with Contributing to Open Source | Video](https://youtu.be/RGd5cOXpCQw)
- [Contributing to Open-Source Projects as a New Python Developer | Video](https://youtu.be/jTTf4oLkvaM)
- [How to Contribute to an Open Source Python Project | Blog post](https://www.educative.io/blog/contribue-open-source-python-project)

### Git

The Param source code is stored in a [Git](https://git-scm.com) source control repository. The first step to working on Param is to install Git onto your system. There are different ways to do this, depending on whether you use Windows, Mac, or Linux.

To install Git on any platform, refer to the [Installing Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) section of the [Pro Git Book](https://git-scm.com/book/en/v2).

To contribute to Param, you will also need [Github account](https://github.com/join) and knowledge of the [_fork and pull request workflow_](https://docs.github.com/en/get-started/quickstart/contributing-to-projects).

### Pixi

Developing all aspects of Param requires a wide range of packages in different environments. To make this more manageable, Pixi manages the developer experience. To install Pixi, follow [this guide](https://pixi.sh/latest/#installation).

#### Glossary

- Tasks: A task is what can be run with `pixi run <task-name>`. Tasks can be anything from installing packages to running tests.
- Environments: An environment is a set of packages installed in a virtual environment. Each environment has a name; you can run tasks in a specific environment with the `-e` flag.
  For example, `pixi run -e test-core test-unit` will run the `test-unit` task in the `test-core` environment.
- Lock-file: A lock-file is a file that contains all the information about the environments.

For more information, see the [Pixi documentation](https://pixi.sh/latest/).

:::{admonition} Note
:class: info

The first time you run `pixi`, it will create a `.pixi` directory in the source directory.
This directory will contain all the files needed for the virtual environments.
The `.pixi` directory can be large, so it is advised not to put the source directory into a cloud-synced directory.
:::

## Installing the Project

### Cloning the Project

The source code for the Param project is hosted on [GitHub](https://github.com/holoviz/param). The first thing you need to do is clone the repository.

1. Go to [github.com/holoviz/param](https://github.com/holoviz/param)
2. [Fork the repository](https://docs.github.com/en/get-started/quickstart/contributing-to-projects#forking-a-repository)
3. Run in your terminal: `git clone https://github.com/<Your Username Here>/param`

The instructions for cloning above created a `param` directory at your file system location.
This `param` directory is the _source checkout_ for the remainder of this document, and your current working directory is this directory.

### Fetch tags from upstream

The version number of the package depends on [`git tags`](https://git-scm.com/book/en/v2/Git-Basics-Tagging), so you need to fetch the tags from the upstream repository:

```bash
git remote add upstream https://github.com/holoviz/param.git
git fetch --tags upstream
git push --tags
```

## Start developing

To start developing, run the following command

```bash
pixi install
```

The first time you run it, it will create a `pixi.lock` file with information for all available environments. This command will take a minute or so to run.

All available tasks can be found by running `pixi task list`, the following sections will give a brief introduction to the most common tasks.

### Editable install

It can be advantageous to install Param in [editable mode](https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs):

```bash
pixi run install
```

:::{admonition} Note
:class: info

Currently, this needs to be run for each environment. So, if you want to install in the `test-312` environment, you can add `--environment` / `-e` to the command:

```bash
pixi run -e test-313 install
```

You can find the list of environments in the **pixi.toml** file or via the command `pixi info`.

:::

## Linting

Param uses [pre-commit](https://pre-commit.com/) to apply linting to Param code. Linting can be run for all the files with:

```bash
pixi run lint
```

Linting can also be set up to run automatically with each commit; this is the recommended way because if linting is not passing, the [Continuous Integration](https://en.wikipedia.org/wiki/Continuous_integration) (CI) will also fail.

```bash
pixi run lint-install
```

## Testing

To help keep Param maintainable, all Pull Requests (PR) with code changes should typically be accompanied by relevant tests. While exceptions may be made for specific circumstances, the default assumption should be that a Pull Request without tests will not be merged.

There are three types of tasks and five environments related to tests.

### Unit tests

Unit tests are usually small tests executed with [pytest](https://docs.pytest.org). They can be found in `param/tests/`.
Unit tests can be run with the `test-unit` task:

```bash
pixi run test-unit
```

The task is available in the following environments:

1. `test-39`, `test-310`, `test-311`, `test-312`, and `test-313`.
1. `test-core`

Where the first ones have the same environments except for different Python versions. `test-core` only has a core set of dependencies.
If you haven't set the environment flag in the command, a menu will help you select which one of the environments to use.

### Example tests

Param's documentation consists mainly of Jupyter Notebooks. The example tests execute all the notebooks and fail if an error is raised. Example tests are possible thanks to [nbval](https://nbval.readthedocs.io/) and can be found in the `doc/` folder.
Example tests can be run with the following command:

```bash
pixi run test-example
```

This task has the same environments as the unit tests except for `test-core`.

## Documentation

The documentation can be built with the command:

```bash
pixi run docs-build
```

## Build

Param has two build tasks, for building packages for Pip and Conda.

```bash
pixi run build-pip
pixi run build-conda
```

## Continuous Integration

Every push to the `main` branch or any PR branch on GitHub automatically triggers a test build with [GitHub Actions](https://github.com/features/actions).

You can see the list of all current and previous builds at [this URL](https://github.com/holoviz/param/actions)

### Etiquette

GitHub Actions provides free build workers for open-source projects. A few considerations will help you be considerate of others needing these limited resources:

- Run the tests locally before opening or pushing to an opened PR.

- Group commits to meaningful chunks of work before pushing to GitHub (i.e., don't push on every commit).

## Useful Links

- [Dev version of Param Site](https://holoviz-dev.github.io/param)
  - Use this to explore new, not yet released features and docs
