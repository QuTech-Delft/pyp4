"""Unit tests for the Processor base class."""

import pytest

from pyp4.processor import Processor


class MockProcessor(Processor):
    def input(self, port_in_meta, packet_in):
        pass


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/basic.json"


@pytest.fixture()
def processor():
    return MockProcessor()


def test_process_load(processor, process):
    with pytest.raises(RuntimeError):
        assert processor.table("ingress", "MyIngress.operations")

    processor.load(process)
    assert processor.table("ingress", "MyIngress.operations")

    process = processor.unload()
    with pytest.raises(RuntimeError):
        assert processor.table("ingress", "MyIngress.operations")
    assert process.blocks["ingress"].tables["MyIngress.operations"]
