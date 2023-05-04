# Developer guide

## Setup

The source code for `Param` is hosted on GitHub. To clone the source repository, issue the following command:

```bash
git clone https://github.com/holoviz/param.git
```

This will create a `param` directory at your file system location.

`Param` relies on `hatch` to manage the project. Follow the [instructions](https://hatch.pypa.io/latest/install/) to install it. Once installed, run the following command to create the *default* environment and activate it, it contains the dependencies required to develop `Param`:

```bash
hatch shell
```

## Testing

The simplest way to run the unit tests is to run the following command:

```bash
hatch run tests
```

You can also run the examples tests, i.e. check that the notebooks run without any error, with:

```bash
hatch run examples
```

## Documentation building

Run the following command to build the documentation:

```bash
hatch run docs:build
```

Once completed, the built site can be found in the `builtdocs` folder.
