import typing as ty
from abc import ABC, abstractmethod
from copy import deepcopy

from qiskit import QuantumCircuit
from qiskit.circuit import Gate
from qiskit.ignis.mitigation.dd._utils import (
    translate_circuit_to_basis,
    get_circuit_duration,
    to_dt_rounded,
)
from qiskit.ignis.mitigation.dd.exceptions import ComponentNotScalable, GateNotFound
from qiskit.providers.models import BackendProperties, BackendConfiguration
from qiskit.pulse import Schedule

"""Base classes to represent a dynamical decoupling component."""


class BaseDynamicalDecouplingComponent(ABC):
    def __init__(
        self,
        name: str,
        durations_map: ty.Callable[[ty.Tuple[int, ...]], int],
        is_scalable: bool = False,
    ):
        """Base class for dynamical decoupling components.

        A component here is anything that is part of a dynamical decoupling scheme.
        It is generic enough to be able to include:
        - Delay gates
        - Any quantum gate implemented by the QuantumCircuit class
        - Any pulse schedule

        Args:
            name: name of the component.
            durations_map: a mapping from qargs to durations in dt. The callable
                should map each input qubit indices list to the duration of the
                component when applied on the given qubits.
            is_scalable: a boolean flag indicating if the gate duration can be scaled.
        """
        self._name = name
        self._durations_map = durations_map
        self._is_scalable = is_scalable

    def _assert_can_be_scaled(self) -> None:
        """Assert that the current component can be scaled or raise an exception.

        Raises:
            ComponentNotScalable: when the component is not scalable.
        """
        if not self._is_scalable:
            raise ComponentNotScalable(self.name)

    @abstractmethod
    def apply(
        self,
        dd_sequence: QuantumCircuit,
        qargs: ty.Tuple[int, ...],
        local_dd_sequence_qargs: ty.Tuple[int, ...],
    ) -> None:
        """Construct and return the implementation of the component.

        Args:
            dd_sequence: the dynamical decoupling sequence on which to append the
                current component.
            qargs: the hardware qubits the dynamical decoupling sequence is supposed
                to be applied on in the end.
            local_dd_sequence_qargs: the qubit indices of the given dd_sequence where
                the component should be applied.
        """

    @abstractmethod
    def scale_to(self, duration: int) -> "BaseDynamicalDecouplingComponent":
        """Scale a copy of the component to the given duration and returns the copy.

        Args:
            duration: duration of the newly created sequence in dt.

        Returns:
            a new instance of BaseDynamicalDecouplingComponent that takes the
            given duration.
        """
        ret = deepcopy(self)
        ret._durations_map = lambda tup: duration
        return ret

    @property
    def is_scalable(self) -> bool:
        """True if the component duration can be rescaled, false otherwise."""
        return self._is_scalable

    def duration(self, qargs: ty.Tuple[int, ...]) -> int:
        """Returns the duration of the sequence in seconds."""
        return self._durations_map(qargs)

    @property
    def name(self):
        return self._name


class DynamicalDecouplingDelayComponent(BaseDynamicalDecouplingComponent):
    def __init__(self, pause_time: int = 1):
        """Dynamical decoupling component implementing a delay.

        Args:
            pause_time: time of the delay in dt. There is a default value because
                most of the delays created will ultimately be scaled so the actual
                delay duration is often not meaningful at the instance creation.
        """
        super(DynamicalDecouplingDelayComponent, self).__init__(
            "delay", lambda qargs: pause_time, is_scalable=True
        )

    def apply(
        self,
        dd_sequence: QuantumCircuit,
        qargs: ty.Tuple[int, ...],
        local_dd_sequence_qargs: ty.Tuple[int, ...],
    ) -> None:
        dd_sequence.delay(self.duration(qargs), qarg=local_dd_sequence_qargs, unit="dt")

    def scale_to(self, duration: int) -> "DynamicalDecouplingDelayComponent":
        return DynamicalDecouplingDelayComponent(duration)


class DynamicalDecouplingGateComponent(BaseDynamicalDecouplingComponent):
    def __init__(
        self,
        gate_name: str,
        configuration: BackendConfiguration,
        properties: BackendProperties,
    ):
        """Dynamical decoupling component implementing a gate.

        Args:
            gate_name: the name of the gate to use. This should correspond to one of
                the methods of the QuantumCircuit class implementing a 1-qubit gate
                without any additional parameters (no rotation gates parametrised
                with an angle for example) when changed to lower case.
        """
        # Create a circuit with the gate
        gate_name = gate_name.lower()
        if not hasattr(QuantumCircuit, gate_name):
            raise GateNotFound(gate_name)
        circuit = QuantumCircuit(1)
        getattr(circuit, gate_name)(0)
        # Unroll it to the backend basis
        unrolled_circuit = translate_circuit_to_basis(circuit, configuration)

        super(DynamicalDecouplingGateComponent, self).__init__(
            gate_name.lower(),
            lambda qargs: to_dt_rounded(
                *get_circuit_duration(unrolled_circuit, properties, qargs),
                configuration.dt
            ),
            is_scalable=False,
        )
        self._circuit = unrolled_circuit

    def apply(
        self,
        dd_sequence: QuantumCircuit,
        _: ty.Tuple[int, ...],
        local_dd_sequence_qargs: ty.Tuple[int, ...],
    ) -> None:
        dd_sequence.compose(
            self._circuit, qubits=list(local_dd_sequence_qargs), inplace=True
        )

    def scale_to(
        self, duration: ty.Union[int, float]
    ) -> "DynamicalDecouplingGateComponent":
        raise ComponentNotScalable(self.name)


class DynamicalDecouplingPulseComponent(BaseDynamicalDecouplingComponent):
    def __init__(
        self,
        name: str,
        schedules: ty.Dict[ty.Tuple[int, ...], Schedule],
    ):
        """Dynamical decoupling component implemented with a pulse Schedule.

        Using pulses instead of gates enable several low-level optimisations and let
        the user have more control on the dynamical decoupling in general.

        Args:
            schedules: pulse(s) to use as a dynamical decoupling component.
        """

        super(DynamicalDecouplingPulseComponent, self).__init__(
            name,
            lambda qargs: schedules[qargs].duration,
            is_scalable=False,
        )
        self._schedules = schedules
        self._gates = {
            qargs: Gate(schedule.name + "_" + "_".join(map(str, qargs)), 1, params=[])
            for qargs, schedule in schedules.items()
        }

    def apply(
        self,
        dd_sequence: QuantumCircuit,
        qargs: ty.Tuple[int, ...],
        local_dd_sequence_qargs: ty.Tuple[int, ...],
    ) -> None:
        dd_sequence.append(self._gates[qargs], qargs=local_dd_sequence_qargs)
        dd_sequence.add_calibration(
            self._gates[qargs],
            qubits=local_dd_sequence_qargs,
            schedule=self._schedules[qargs],
        )

    def scale_to(
        self, duration: ty.Union[int, float]
    ) -> "DynamicalDecouplingGateComponent":
        raise ComponentNotScalable(self.name)
