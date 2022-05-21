import json
import logging
import sys
import time

from pyp4 import PacketIO
from pyp4.packet import HeaderStack, Header
from pyp4.processors.v1model import (
    V1ModelProcessor,
    V1ModelRuntimeAbc,
    V1ModelProcess,
    V1ModelPortMeta,
)


def print_message(message):
    print("=" * len(message))
    print(message)
    print("=" * len(message))


class V1ModelDevice:

    def __init__(self, program_file_name):
        runtime = V1ModelRuntime()
        with open(program_file_name) as program_file:
            program = json.load(program_file)
        process = V1ModelProcess("V1ModelDevice", program, PacketIO.STACK)
        self.__processor = V1ModelProcessor(runtime).load(process)

    def process(self, port_in, packet_in):
        # Wrap in processor specific port_meta
        port_in_meta = V1ModelPortMeta(standard_metadata={"ingress_port": port_in})

        # Actual processing
        port_packets = self.__processor.input(port_in_meta, packet_in)

        # Unwrap processor specific port_meta
        return [
            (port_meta.standard_metadata["egress_port"], packet)
            for port_meta, packet in port_packets
        ]


class V1ModelRuntime(V1ModelRuntimeAbc):
    def __init__(self):
        self.__start_time = int(time.time() * 1_000_000)

    def time(self):
        return int(time.time() * 1_000_000) - self.__start_time


def main():
    device = V1ModelDevice("./examples/ping/p4/ping.json")

    header = Header([("count", 32, False)])
    header["count"].val = 0
    packet = HeaderStack()
    packet.push(header)

    port_in = 5

    print_message(f"=== Injecting packet {packet} on port {port_in} ===")

    port_packets_out = device.process(port_in, packet)
    assert len(port_packets_out) == 1

    (port_out, packet), = port_packets_out
    assert port_out == port_in

    print_message(f"=== Received packet {packet} on port {port_out} ===")

    header = packet.pop()
    assert header["count"].val == 1


if __name__ == "__main__":
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)5s: %(name)s :: %(message)s"))
    logger = logging.getLogger("pyp4")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    main()
