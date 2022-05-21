"""Unit tests for the Process base class."""

import copy
import pytest

from pyp4.process import Process


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/basic.json"


def test_missing_element(program):
    program = copy.deepcopy(program)
    del program["parsers"]
    with pytest.raises(TypeError, match=r"Program is required to have parser\(s\)"):
        Process._validate_program_pipeline(program, ["parser"], ["ingress", "egress"], ["deparser"])


def test_incorrect_length(program):
    with pytest.raises(TypeError, match=r"Program must have 3 pipeline\(s\) : .*"):
        Process._validate_program_pipeline(
            program, ["parser"], ["ingress", "egress", "zegress"], ["deparser"],
        )


def test_incorrect_name(program):
    with pytest.raises(TypeError, match=r"Program must have a deparser called \"zeparser\" : .*"):
        Process._validate_program_pipeline(
            program, ["parser"], ["ingress", "egress"], ["zeparser"],
        )


def test_enums(process):
    # Currently, there are no test programs with enums.
    assert process.enums == {}
