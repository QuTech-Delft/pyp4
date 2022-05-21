# Ping Pong example

This example illustrates basic usage of PyP4 by creating a Device based on the V1Model processor
provided by this package.

## Instructions

Run this example from the top-level directory:
```
python3 -m examples.ping.run
```

This will load the program from [`p4/ping.json`](p4/ping.json) which was compiled from
[`p4/ping.p4`](p4/ping.p4).

## What you will see

The script pings the Device which will increment the `count` field in its header.
