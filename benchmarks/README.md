# Benchmarking

`Param` uses ASV (https://asv.readthedocs.io) for benchmarking.

## Preparation

Install `asv` into your environment with for example:
```
hatch shell
cd benchmarks
pip install asv
```

ASV then runs benchmarks in isolated virtual environments that it creates using `virtualenv`.

## Running benchmarks

To run all benchmarks against the default `main` branch:
```
cd benchmarks
asv run
```

The first time this is run it will create a machine file to store information about your machine. Then a virtual environment will be created and each benchmark will be run multiple times to obtain a statistically valid benchmark time.

To list the benchmark timings stored for the `main` branch use:
```
asv show main
```

ASV ships with its own simple webserver to interactively display the results in a webbrowser. To use this:
```
asv publish
asv preview
```
and then open a web browser at the URL specified.

If you want to quickly run all benchmarks once only to check for errors, etc, use:
```
asv dev
```
instead of `asv run`.


## Adding new benchmarks

Add new benchmarks to existing or new classes in the `benchmarks/benchmarks` directory. Any class member function with a name that starts with `time` will be identified as a timing benchmark when `asv` is run.

Data that is required to run benchmarks is usually created in the `setup()` member function. This ensures that the time taken to setup the data is not included in the benchmark time. The `setup()` function is called once for each invocation of each benchmark, the data are not cached.

At the top of each benchmark class there are lists of parameter names and values. Each benchmark is repeated for each unique combination of these parameters.

If you only want to run a subset of benchmarks, use syntax like:
```
asv run -b ShadeCategorical
```
where the text after the `-b` flag is used as a regex to match benchmark file, class and function names.


## Benchmarking code changes

You can compare the performance of code on different branches and in different commits. Usually if you want to determine how much faster a new algorithm is, the old code will be in the `main` branch and the new code will be in a new feature branch. Because ASV uses virtual environments and checks out the `param` source code into these virtual environments, your new code must be committed into the new feature branch locally.

To benchmark the latest commits on `main` and your new feature branch, edit `asv.conf.json` to change the line
```
"branches": ["main"],
```
into
```
"branches": ["main", "new_feature_branch"],
```
or similar.

Now when you `asv run` the benchmarks will be run against both branches in turn.

Then use
```
asv show
```
to list the commits that have been benchmarked, and
```
asv compare commit1 commit2
```
to give you a side-by-side comparison of the two commits.

You can run `asv` for single tags and compare them
```
asv run v0.0.1^!
asv run v0.0.2^!
asv compare v0.0.1 v0.0.2
```

```
asv run v0.0.2..HEAD
