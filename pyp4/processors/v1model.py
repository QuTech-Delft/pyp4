"""V1Model processor."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pyp4 import PacketIO
from pyp4.packet import FixedInt
from pyp4.process import Process
from pyp4.processor import Processor


class V1ModelProcessor(Processor):
    """Processor for the V1Model architecture.

    For more details, see https://github.com/p4lang/p4c/blob/master/p4include/v1model.p4.

    Parameters
    ----------
    runtime : `pyp4.processors.v1model.V1ModelRuntimeAbc`
        The runtime instance for the V1Model.

    """

    def __init__(self, runtime):
        # This processor requires a runtime
        assert runtime is not None
        super().__init__(runtime)

    @property
    def __parser(self):
        return self._process.parsers["parser"]

    @property
    def __ingress(self):
        return self._process.blocks["ingress"]

    @property
    def __egress(self):
        return self._process.blocks["egress"]

    @property
    def __deparser(self):
        return self._process.deparsers["deparser"]

    @staticmethod
    def __check_field(field_name, standard_metadata):
        if field_name not in standard_metadata:
            raise ValueError(f"Field {field_name} was not provided in standard_metadata")

    @staticmethod
    def __initialise_metadata(bus, port_in_meta):
        standard_metadata = bus.metadata["standard_metadata"]

        # Check the provided standard_metadata.
        V1ModelProcessor.__check_field("ingress_port", port_in_meta.standard_metadata)

        # Copy over the input standard_metadata.
        for field, value in port_in_meta.standard_metadata.items():
            standard_metadata[field].val = value

        # Initialise certain fields to architecture-specific values.
        standard_metadata["egress_spec"].set_max_val()

    def __ingress_process(self, bus):
        bus.metadata["standard_metadata"]["ingress_global_timestamp"].val = int(
            self._runtime.time())
        self.__ingress.process(bus)

    @staticmethod
    def __replication(bus):
        bus_list = []
        if not bus.metadata["standard_metadata"]["egress_spec"].is_max_val():
            bus_list.append(bus)
        return bus_list

    def __egress_process(self, bus_list):
        for bus in bus_list:
            bus.metadata["standard_metadata"]["egress_port"].val = (
                bus.metadata["standard_metadata"]["egress_spec"].val)
            bus.metadata["standard_metadata"]["egress_global_timestamp"].val = int(
                self._runtime.time())

            self.__egress.process(bus)

            if bus.metadata["standard_metadata"]["egress_spec"].is_max_val():
                bus.packet.clear()

    @staticmethod
    def __emit(bus_packet_out_list):
        port_packet_out = []
        for bus, packet_out in bus_packet_out_list:
            if packet_out:
                port_out_meta = V1ModelPortMeta(
                    standard_metadata=bus.metadata["standard_metadata"].as_dict()
                )
                port_packet_out.append((port_out_meta, packet_out))

        return port_packet_out

    def input(self, port_in_meta, packet_in):
        """Process an incoming packet.

        The input packet is consumed and the output packets are brand new object.

        Parameters
        ----------
        port_in_meta : `pyp4.processors.v1model.V1ModelPortMeta`
            Input port metadata.
        packet_in : `<process specific Packet>`
            The input packet.

        Returns
        -------
        list of tuple of (`pyp4.processors.v1model.V1ModelPortMeta`, `<process specific Packet`)
            One tuple of the output port metadata and the packet for each output packet

        """
        bus = self._process.bus()

        # ------------------------------------------------------------------------------------------
        # Initialise metadata.
        # ------------------------------------------------------------------------------------------

        self.__initialise_metadata(bus, port_in_meta)

        # ------------------------------------------------------------------------------------------
        # Parser
        # ------------------------------------------------------------------------------------------

        self.__parser.process(bus, packet_in)

        # ------------------------------------------------------------------------------------------
        # Ingress
        # ------------------------------------------------------------------------------------------

        self.__ingress_process(bus)

        # ------------------------------------------------------------------------------------------
        # Replication
        # ------------------------------------------------------------------------------------------

        bus_list = self.__replication(bus)

        # ------------------------------------------------------------------------------------------
        # Egress
        # ------------------------------------------------------------------------------------------

        self.__egress_process(bus_list)

        # ------------------------------------------------------------------------------------------
        # Deparser
        # ------------------------------------------------------------------------------------------

        bus_packet_out_list = [(bus, self.__deparser.process(bus.packet)) for bus in bus_list]

        # ------------------------------------------------------------------------------------------
        # Emit
        # ------------------------------------------------------------------------------------------

        return self.__emit(bus_packet_out_list)


@dataclass
class V1ModelPortMeta:
    """V1Model port metadata."""

    standard_metadata: dict


class V1ModelRuntimeAbc(ABC):
    """The abstract base class for a V1Model runtime."""

    @abstractmethod
    def time(self):
        """Get the simulated time.

        Returns
        -------
        `int`
            The current time on the device in microseconds. The clock must be set to 0 every time
            the switch starts.

        """
        raise NotImplementedError


class V1ModelExtern:
    """The V1Model extern functionality class.

    Parameters
    ----------
    program : dict
        The program in BM JSON format.

    """

    def __init__(self, program):
        self.__registers = {reg["name"]: Register(reg) for reg in program["register_arrays"]}

    @staticmethod
    def extern_assert(val):
        """Execute the assert extern.

        Parameters
        ----------
        val : `pyp4.packet.FixedInt`
            The value to be asserted.

        """
        assert bool(val)

    @staticmethod
    def assume(val):
        """Execute the assume extern.

        Outside of formal verification tools, assume is equivalent to and assert.

        Parameters
        ----------
        val : `pyp4.packet.FixedInt`
            The value to be assumed.

        """
        assert bool(val)

    @staticmethod
    def log_msg(msg, data):
        """Execute the log_msg extern.

        Parameters
        ----------
        msg : `str`
            The message to log.
        data : `Any`
            Arguments to print in the string.

        """
        print(msg.format(*data))

    @staticmethod
    def mark_to_drop(standard_metadata):
        """Execute the mark_to_drop extern.

        Parameters
        ----------
        standard_metadata : `pyp4.packet.Header`
            The standard metadata.

        """
        standard_metadata["egress_spec"].set_max_val()

    def register_read(self, lval, register_name, index):
        """Execute the register read extern.

        Parameters
        ----------
        lval : `pyp4.packet.FixedInt`
            The value in which the read value is to be stored.
        register_name : `str`
            The name of the register.
        index : `pyp4.packet.FixedInt`
            The index of the register from which to read.

        """
        lval.val = self.__registers[register_name][int(index)].val

    def register_write(self, register_name, index, rval):
        """Execute the register write extern.

        Parameters
        ----------
        register_name : `str`
            The name of the register.
        index : `pyp4.packet.FixedInt`
            The index of the register into which to write to.
        rval : `pyp4.packet.FixedInt`
            The value that is to be written into the register.

        """
        self.__registers[register_name][int(index)].val = int(rval)


class Register:
    """A P4 register.

    Parameters
    ----------
    bm_register : dict
        Register definition in BM JSON format.

    """

    def __init__(self, bm_register):
        self.__bm_register = bm_register

        self.__entries = []
        for _ in range(self.__bm_register["size"]):
            self.__entries.append(FixedInt(0, self.__bm_register["bitwidth"]))

    def __getitem__(self, index):
        """Return a register entry."""
        return self.__entries[index]


class V1ModelProcess(Process):
    """The V1Model process.

    Parameters
    ----------
    name : `str`
        The process name.
    program : `dict`
        The program to execute in the BM format.
    packet_io : `pyp4.PacketIO`
        External packet representation type.

    """

    def __init__(self, name, program, packet_io=PacketIO.BINARY):
        extern = V1ModelExtern(program)
        super().__init__(name, program, packet_io, extern)

    @staticmethod
    def _validate_program(program):
        Process._validate_program_pipeline(
            program, ["parser"], ["ingress", "egress"], ["deparser"],
        )
