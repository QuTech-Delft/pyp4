"""Mock devices for tests."""

import time

from pyp4 import PacketIO
from pyp4.processors.v1model import (
    V1ModelProcessor,
    V1ModelRuntimeAbc,
    V1ModelProcess,
    V1ModelPortMeta,
)


class MockV1ModelDevice():

    def __init__(self, program):
        runtime = MockV1ModelRuntime()
        process = V1ModelProcess("MockV1Model", program, PacketIO.STACK)
        self.__processor = V1ModelProcessor(runtime).load(process)

    @property
    def processor(self):
        return self.__processor

    def port_in_meta(self, ingress_port):
        return V1ModelPortMeta(standard_metadata={"ingress_port": ingress_port})


class MockV1ModelRuntime(V1ModelRuntimeAbc):

    def __init__(self):
        super().__init__()
        self.__start_time = int(time.time() * 1_000_000)

    def time(self):
        return int(time.time() * 1_000_000) - self.__start_time
