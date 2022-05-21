# PyP4: P4 for Python

[![pipeline
status](https://gitlab.tudelft.nl/qp4/pyp4/badges/master/pipeline.svg)](https://gitlab.tudelft.nl/qp4/pyp4/commits/master)
[![coverage
report](https://gitlab.tudelft.nl/qp4/pyp4/badges/master/coverage.svg)](https://gitlab.tudelft.nl/qp4/pyp4/commits/master)

## Introduction

The PyP4 python package provides a library for running P4 pipelines in the [BMv2 JSON
format](https://github.com/p4lang/behavioral-model/blob/main/docs/JSON_format.md) on Python-based
network simulators. This package is designed to be used as an external library for concrete
implementations on particular simulators. The implementations can then instantiate a P4 processor on
each node and inject (pseudo-)packets and handle the output (pseudo-)packets.

This package implements all the core P4 features, provides implementations (the non
simulator-specific parts) of processors for a selection of P4 architectures that are supported by
the mainline P4 compiler. It also provides a well defined interface for integrating custom P4
architectures and their extern functionality.

### Why PyP4 exists

PyP4 was created to enable P4 pipelines on the [NetSquid](https://netsquid.org) quantum network
simulator which is programmed through Python. It is likely, that this package may not be very useful
non-quantum P4 research and implementations as the C++ BMv2 implementations are generally sufficient
and better for these purposes.

## P4C

To compile the P4 programs to BMv2 a P4 compiler with support for the target P4 architecture is
required. All architectures in this repository can be compiled using the mainline P4C toolchain,
[p4lang/p4c](https://github.com/p4lang/p4c).

## Docs

To build the docs, enter the [`docs`](docs) directory and run
```
make html
```
The resulting documentation can be read by opening
[`docs/build/html/index.html`](docs/build/html/index.html) in a browser.

## Logging

This package executes P4 programs compiled by the user. Naturally, this introduces the possibility
of errors and bugs in the P4 program which the user will want to troubleshoot. To aid this, the PyP4
package provides a hierarchy of loggers to help the user follow the execution of the P4 program.
PyP4 logging provides two knobs for tuning the logging: log level and logger hierarchy.

All logging in `PyP4` is based on Python's in-built `logging` package and thus additional
explanations and documentation can be found by reading the `logging` package documentation.

### Log level

The PyP4 packages uses only two log levels: `INFO` and `DEBUG`.
* `INFO` logs follow the flow of the program's execution. They log which P4 objects are hit during
  the program's execution. This includes the names assigned to these objects in the BMv2 JSON file
  which may not exist in the P4 program itself. Thus, it is important to correlate these logs with
  the BMv2 JSON file as well as the P4 program itself.
* `DEBUG` logs will also include information about what gets executed and, where possible, the
  values that are involved as well as the relevant source code line.

### Logger hierarchy

Each P4 object from the BMv2 JSON gets its own logger for every P4 program instance. This makes it
easy to use the `logging` hierarchy to obtain loggers for specific P4 objects in the code.
* You can get the root PyP4 logger with `logging.getLogger("pyp4")`.
* You can get the root PyP4 logger for a particular program instance, e.g. one called "device", with
  `logging.getLogger("pyp4.device")`.
* You can get the root logger for parsers on that device with
  `logging.getLogger("pyp4.device.parser")`.
* Some P4 objects split again (e.g. parsers have parse states) which you can get with
  `logging.getLogger("pyp4.device.parser.ParseState")`.
* You can get a specific parse state, in this case the parse state with the name "start", with
  `logging.getLogger("pyp4.device.parser.ParseState.start")`. Note that the name used is the one in
  the BMv2 JSON file which may or may not line up with the original P4 program.

The same logic applies to other P4 objects. To find out what loggers get created, create a `Program`
object that loads your BMv2 JSON file and log the root PyP4 logger with log level set to `DEBUG`.
This will log the names of the loggers created. Printing the name of the logger using the
`"%(name)s"` format may also help you identify which specific loggers you are interested in.

Note that there is no single logger that will allow you to log a particular class of P4 program
objects on all devices. This requires collecting the appropriate logger from each device and
configuring them individually.

### Example

We provide a ready-to-run snippet for those who are not familiar with the `logging` module and how
to configure it. For more configuration options, please refer to the ['logging'
documentation](https://docs.python.org/3/library/logging.html).

To log all PyP4 logs to `stdout` include the following snippet before running any PyP4 code.
```
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(levelname)5s: %(message)s"))
logger = logging.getLogger("pyp4")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
```
Note that we explicitly use `logging.getLogger` instead of `logging.basicConfig` as it's easier to
reuse this snippet to make use of the logger hierarchy in PyP4.

## Integrations with simulators

### Existing integrations

PyP4 has so far been integrated with:
- [NetSquid](https://gitlab.tudelft.nl/qp4/netsquid-p4)

### Guide for integration

*TODO*

## Running tests

To run all unit tests, run
```
make tests
```

This package uses pytest for unit testing so if you need more fine-grained control over which tests
to run, just skip the Makefile and execute call pytest directly.

## Acknowledgements

Bruno Rijsman has contributed much of the code in the original
[netsquid-qp4](https://gitlab.com/softwarequtech/netsquid-snippets/netsquid-qp4) repository, a lot
of which has ended up in PyP4.
