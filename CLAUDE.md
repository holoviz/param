# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Param is a zero-dependency Python library providing declarative, validated parameters for Python classes and a reactive programming API (`rx`). It requires Python >= 3.10. Param is the backbone for Panel and HoloViews in the HoloViz ecosystem.

## Development Setup

This project uses **pixi** for environment and task management.

```bash
pixi run setup-dev    # Editable install + pre-commit hooks
```

## Common Commands

```bash
# Testing
pixi run test-unit                    # Run all unit tests
pixi run -e test-312 test-unit        # Run tests in a specific Python environment
pytest tests/testparameterizedobject.py  # Run a single test file
pytest tests/testparameterizedobject.py::TestParameterized::test_name  # Run a single test
pixi run test-example                 # Run notebook/example tests

# Linting
pixi run lint                         # Run pre-commit hooks (ruff + misc checks)
pixi run lint-install                 # Install pre-commit hooks

# Docs
pixi run -e docs docs-build           # Build docs with sphinx

# Build
pixi run -e build build-pip            # Build wheel/sdist
pixi run -e build build-conda          # Build conda package
```

## Test Configuration

- pytest with `filterwarnings = ["error"]` and `xfail_strict = true` — all warnings are errors and xfail tests must actually fail
- `conftest.py` sets `PARAM_PARAMETER_SIGNATURE=1` and `param.parameterized.warnings_as_exceptions = True`
- `asyncio_mode = "auto"` — async tests run automatically without `@pytest.mark.asyncio`
- Test environments: `test-310` through `test-314`, `test-314t` (free-threading), `test-core` (minimal deps)

## Code Architecture

The `param/` package has a small number of tightly coupled modules:

- **`parameterized.py`** — Core foundation. Defines `Parameter` (the descriptor base class), `Parameterized` (the base class for all param-using classes), and `ParameterizedMetaclass`. Contains the watch/callback event system, messaging/logging infrastructure, and `script_repr` serialization.

- **`parameters.py`** — All concrete Parameter types (`Number`, `Integer`, `String`, `Boolean`, `List`, `Dict`, `Selector`, `ClassSelector`, `Path`, `Date`, `DataFrame`, `Array`, etc.). Each Parameter type implements validation, serialization, and type-specific behavior. Depends on `parameterized.py`.

- **`reactive.py`** — The `rx` reactive expression framework and `bind()` function. Provides lazy evaluation, operator overloading, and dynamic dependency tracking for building reactive pipelines. Depends on `parameterized.py`.

- **`depends.py`** — The `@depends` decorator for declaring method dependencies on parameters.

- **`_utils.py`** — Internal utilities: type checking, validation helpers, `descendents`/`concrete_descendents`, `exceptions_summarized`.

- **`serializer.py`** — Parameter serialization/deserialization support.

- **`ipython.py`** — IPython/Jupyter integration.

- **`__init__.py`** — Re-exports the full public API. The public API surface is entirely defined here.

**`numbergen/`** — Separate package for number generation utilities, bundled with param.

### Key Design Patterns

- **Descriptor protocol**: `Parameter` subclasses are Python descriptors (`__get__`/`__set__`/`__delete__`) on `Parameterized` classes. They store per-instance values and enforce validation.
- **Metaclass**: `ParameterizedMetaclass` handles parameter inheritance, merging parameter declarations from parent classes, and building the class parameter namespace.
- **Observer/watch pattern**: `obj.param.watch(callback, ['param_name'])` registers callbacks that fire on parameter changes. This is the core of param's reactivity.

## Linting

Ruff with rules `D, W, E, F` (numpy docstring convention). Many rules are intentionally ignored — see `pyproject.toml [tool.ruff.lint]` for the ignore list. Pre-commit also runs `check-builtin-literals`, `check-case-conflict`, `end-of-file-fixer`, `trailing-whitespace`, and notebook cleaning.
