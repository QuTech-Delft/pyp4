"""P4 actions."""

from pyp4 import expr
from pyp4.trace import get_logger, Trace

logger = get_logger(__name__)


class Action:
    """A P4 action.

    Parameters
    ----------
    process_name : `str`
        The name of the process running the P4 program.
    bm_action : dict
        Action definition in BM JSON format.
    extern : `<processor specific ExternClass>`, optional
        Processor specific object for handling externs.

    """

    @Trace(logger)
    def __init__(self, process_name, bm_action, extern):
        self.__process_name = process_name
        self.__bm_action = bm_action
        self.__extern = extern
        self.logger = None

    @property
    def name(self):
        """`str`: Name of the action."""
        return self.__bm_action["name"]

    @property
    def process_name(self):
        """`str`: Name of the process running the P4 program this action belongs to."""
        return self.__process_name

    @Trace(logger)
    def process(self, bus, runtime_data):
        """Execute the action.

        Parameters
        ----------
        bus : `pyp4.packet.Bus`
            The metadata + headers bus.
        runtime_data : list of `str`
            The runtime parameters.

        """
        for prim in self.__bm_action["primitives"]:
            self.logger.debug(
                f"op-{prim['op']}-\"{prim.get('source_info', {}).get('source_fragment', '')}\""
            )
            if prim["op"] == "assign":
                assert len(prim["parameters"]) == 2
                left = expr.lval(bus, prim["parameters"][0], runtime_data)
                right = expr.rval(bus, prim["parameters"][1], runtime_data)
                self.logger.debug(f"rval={right}")
                left.val = right

            elif prim["op"] == "remove_header":
                assert len(prim["parameters"]) == 1
                param = prim["parameters"][0]
                assert param["type"] == "header"

                hdr_name = param["value"]
                if hdr_name in bus.packet:
                    hdr = bus.get_hdr(hdr_name)
                    hdr.set_invalid()

            elif prim["op"] == "add_header":
                assert len(prim["parameters"]) == 1
                param = prim["parameters"][0]
                assert param["type"] == "header"
                bus.packet.add_header(param["value"])

            else:
                assert self.__extern is not None

                extern_func_name = prim["op"]

                # If an extern clashes with a python keyword prepend with extern_
                if extern_func_name in set(["assert"]):
                    extern_func_name = f"extern_{extern_func_name}"

                extern_func = getattr(self.__extern, extern_func_name)

                param_list = tuple(
                    expr.param(bus, param, runtime_data) for param in prim["parameters"]
                )

                self.logger.debug(f"{extern_func_name}{param_list}")
                extern_func(*param_list)
