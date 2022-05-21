"""Special pytest file for shared fixtures."""

import json
import pytest

from pyp4.action import Action
from pyp4 import PacketIO
from pyp4.process import Process
from pyp4.processors.v1model import V1ModelExtern


class MockProcessCls(Process):
    def __init__(self, name, program, packet_io=PacketIO.BINARY):
        super().__init__(name, program, packet_io, None)

    @staticmethod
    def _validate_program(program):
        pass


@pytest.fixture(scope="session")
def MockProcess():
    return MockProcessCls


@pytest.fixture(scope="module")
def program(program_file_name):
    with open(program_file_name) as program_file:
        yield json.load(program_file)


@pytest.fixture(scope="module")
def process(program):
    return MockProcessCls(__name__, program, PacketIO.STACK)


@pytest.fixture(scope="module")
def actions(program):
    # Process does not provide direct access to the actions so we read them ourselves.
    return {
        act["name"]: Action(__name__, act, None)
        for act in program["actions"]
    }


@pytest.fixture(scope="module")
def v1model_actions(program):
    # Actions for a V1Model architecture.
    return {
        act["name"]: Action(__name__, act, V1ModelExtern(program))
        for act in program["actions"]
    }


@pytest.fixture()
def bus(process):
    return process.bus()
