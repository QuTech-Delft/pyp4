"""Trace utilities for PyP4."""

from abc import ABC, abstractmethod
from functools import partial
import logging


def get_logger(name):
    """Create and initialise a logger.

    Parameters
    ----------
    name : `str`
        The name of the logger to create.

    """
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    return logger


class TraceAbc(ABC):
    """Abstract base class for the Trace decorator.

    Parameters
    ----------
    modlogger : `logging.Logger`
        The logger for the module in which the traced function is located.
    logger_attr_name : `str`
        The attribute name for the logger of the traced class.

    """

    def __init__(self, modlogger, logger_attr_name):
        self.__modlogger = modlogger
        self.__logger_attr_name = logger_attr_name

    @property
    def _modlogger(self):
        return self.__modlogger

    @property
    def _logger_attr_name(self):
        return self.__logger_attr_name

    def __get__(self, obj, objtype):
        return partial(self.__call__, obj)

    @abstractmethod
    def __call__(self, *args, **kwargs):
        raise NotImplementedError


class Trace(TraceAbc):
    """The Trace decorator.

    When applied to an __init__ function, it will create a logger on the create object with the
    provided attribute name. When applied to a method, it will log calls to the decorated method
    using the logger with the provided attribute name. Trace decorated methods require that the
    object's __init__ is also decorated.

    Parameters
    ----------
    modlogger : `logging.Logger`
        The logger for the module in which the traced function is located.
    logger_attr_name : `str`
        The attribute name for the logger of the traced class.

    """

    def __init__(self, modlogger, logger_attr_name="logger"):
        super().__init__(modlogger, logger_attr_name)

    def __call__(self, *args, **kwargs):
        assert callable(args[0])
        function = args[0]
        if function.__name__ == "__init__":
            return TraceInit(self._modlogger, self._logger_attr_name, function)
        return TraceMethod(self._modlogger, self._logger_attr_name, function)


class TraceInit(TraceAbc):
    """The __init__ function Trace object.

    Trace decorated __init__ functions are handled as TraceInit objects.

    Parameters
    ----------
    modlogger : `logging.Logger`
        The logger for the module in which the traced function is located.
    logger_attr_name : `str`
        The attribute name for the logger of the traced class.
    function : `Callable`
        The function that is decorated.

    """

    def __init__(self, modlogger, logger_attr_name, function):
        super().__init__(modlogger, logger_attr_name)
        assert function.__name__ == "__init__"
        self.__init_function = function

    def __call__(self, *args, **kwargs):
        self.__init_function(*args, **kwargs)
        obj = args[0]

        if not hasattr(obj, "name"):
            raise AttributeError(
                f"{obj.__class__.__name__} has no attribute 'name' - "
                f"pyp4.trace.Trace requires the class to provide one"
            )

        if not hasattr(obj, "process_name"):
            raise AttributeError(
                f"{obj.__class__.__name__} has no attribute 'process_name' - "
                f"pyp4.trace.Trace requires the class to provide one"
            )

        if getattr(obj, self._logger_attr_name, None) is not None:
            raise AttributeError(
                f"{self._modlogger.name}.{obj.__class__.__name__} already has an attribute "
                f"'{self._logger_attr_name}' "
                f"- please choose a different name for the object's logger attribute name",
            )

        # Insert the process name between the top-level name and the module name.
        hierarchy = self._modlogger.name.split('.')
        try:
            pyp4_root = hierarchy.index("pyp4")
        except ValueError:
            pyp4_root = -1
        if (pyp4_root + 1) != len(hierarchy):
            hierarchy.insert(pyp4_root + 1, obj.process_name)
        process_logger = get_logger('.'.join(hierarchy))

        object_logger = get_logger(f"{process_logger.name}.{obj.__class__.__name__}.{obj.name}")
        setattr(obj, self._logger_attr_name, object_logger)

        self._modlogger.debug(f"Constructed {object_logger.name}", stacklevel=2)


class TraceMethod(TraceAbc):
    """The __init__ function Trace object.

    Trace decorated methods are handled as TraceMethod objects.

    Parameters
    ----------
    modlogger : `logging.Logger`
        The logger for the module in which the traced function is located.
    logger_attr_name : `str`
        The attribute name for the logger of the traced class.
    function : `Callable`
        The function that is decorated.

    """

    def __init__(self, modlogger, logger_attr_name, function):
        super().__init__(modlogger, logger_attr_name)
        self.__function = function

    def __call__(self, *args, **kwargs):
        try:
            logger = getattr(args[0], self._logger_attr_name)
        except AttributeError as ex:
            raise AttributeError(
                "pyp4.trace.Trace decorated methods require that the class' __init__ is also "
                "pyp4.trace.Trace decorated and that the same logger attribute name is used"
            ) from ex
        # Note that this is not the same as %(funcName)s in logging format. The code below will log
        # the name of the decorated function that is being called. %(funcName)s is the name of the
        # calling function (stacklevel=2) or __call__ (stacklevel=1).
        logger.info(f"{logger.name}", stacklevel=2)
        return self.__function(*args, **kwargs)
