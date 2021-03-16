from qiskit.transpiler.passmanager import PassManager
from qiskit.providers.ibmq.ibmqbackend import IBMQBackend
from .fundamental_state_analysis import FlagFundamentalStateOperations
from .merge_delays import MergeDelaysPass
from .delays_to_dynamical_decoupling import DelayToDynamicalDecouplingSequencePass
from .barriers_to_delays import BarriersToDelaysPass

from qiskit.ignis.mitigation.dd.sequence import BaseDynamicalDecouplingSequence
import typing as ty


def get_dd_pass_manager(
    backend: IBMQBackend,
    dd_sequence: BaseDynamicalDecouplingSequence,
    scheduling: ty.Literal["asap", "alap"] = "alap",
) -> PassManager:
    """Get a PassManager instance to apply dynamical decoupling

    Args:
        backend: the backend used to execute the circuits that will be given to the
            pass manager.
        dd_sequence: dynamical-decoupling sequence to use.
        scheduling: As Late As Possible (alap) or As Soon As Possible (asap).

    Returns:
        a pass manager that includes all the passes needed to add dynamical
        decoupling to the circuits.
    """
    properties = backend.properties()
    configuration = backend.configuration()
    dt: float = configuration.dt
    _fundamental_state_flagger = FlagFundamentalStateOperations()
    _delay_merger = MergeDelaysPass(dt)
    _delay_to_dd = DelayToDynamicalDecouplingSequencePass(dd_sequence, properties, dt)
    _barriers_to_delays = BarriersToDelaysPass(
        properties, dt, scheduling_method=scheduling
    )

    return PassManager(
        passes=[
            _barriers_to_delays,
            _delay_merger,
            _fundamental_state_flagger,
            _delay_to_dd,
        ]
    )
