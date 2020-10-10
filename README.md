# pyfmuxer

An extendable forward proxy and muxer written in Python

## features

* in Python3 with built-in modules, zero dependency
* customizable by registering protocols
* traffic analysis

## Usage

You have to extend the module with your own script

under most circumstances, you only have to import the ForwardMuxer class and instantiate it with address and port to bind to (see example), then register your protocol matching rules.

`ForwardMuxer.register_handler` requires two parameters, followed with three optional parameters. See docstring for explanations.

## Example

go check out the snippets in the `examples` directory.

## Disclaimer

This script is considered a temporary tool for short term use.  
It's NOT production ready.
