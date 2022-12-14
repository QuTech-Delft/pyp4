"""P4 processor framework definition."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from pyp4.process import Process
from pyp4.table import Table


class Processor(ABC):
    """Base class for P4 processors.

    A processor defines the packet processing pipeline. That is, how do the programmable blocks
    defined in the P4 program connect to each other and the fixed-function environment.

    This `Processor` class is an abstract base class for P4 processors. A concrete processor
    subclass must be provided for each P4 architecture.

    A processor relies on a runtime object to provide it with access to a runtime (e.g. a network
    simulator runtime).

    Parameters
    ----------
    runtime : <processor specific Runtime>, optional
        The simulated device's runtime.

    """

    def __init__(self, runtime: Optional[Any] = None):
        self.__process = None
        self.__runtime = runtime

    @property
    def _process(self) -> Process:
        """The P4 process running on this processor."""
        if self.__process is None:
            raise RuntimeError("The processor is currently not running any process")
        return self.__process

    @property
    def _runtime(self) -> Any:
        """<processor specific Runtime>: The simulated device's runtime."""
        return self.__runtime

    def load(self, process: Process) -> 'Processor':
        """Load a process onto the processor possibly replacing the current one.

        Parameters
        ----------
        process
            The P4 process to run on this processor.

        Returns
        -------
        :
            For convenience the processor itself is returned.

        """
        self.__process = process
        return self

    def unload(self) -> Process:
        """Unload the current process from the processor.

        Returns
        -------
        :
            The process that was unloaded.

        """
        process = self.__process
        self.__process = None
        return process

    def table(self, block: str, name: str) -> Table:
        """Access a table in the running P4 process.

        Parameters
        ----------
        block
            The name of the block in which the table is defined. Note that the name is defined by
            the architecture, not the program itself. E.g. the ingress block is called "ingress"
            regardless of how that block is called in the program.
        name
            The name of the table as defined by the program.

        Returns
        -------
        :
             The table.

        """
        if block not in self._process.blocks:
            raise ValueError(f"Block {block} does not exist in this architecture")
        if name not in self._process.blocks[block].tables:
            raise ValueError(f"Block {block} does not have table {name} in this program")
        return self.__process.blocks[block].tables[name]

    @abstractmethod
    def input(self, port_in_meta: Any, packet_in: Any) -> List[Tuple[Any, Any]]:
        """Process an incoming packet.

        The input packet is consumed and the output packets are brand new object.

        Parameters
        ----------
        port_in_meta : <processor specific PortMeta>
            Input port metadata.
        packet_in : <process specific PacketClass>
            The input packet.

        Returns
        -------
        List[Tuple[<processor specific PortMeta>, <process specific PacketClass>]]
            A tuple of the output port metadata and the packet for each output packet

        """
        raise NotImplementedError
