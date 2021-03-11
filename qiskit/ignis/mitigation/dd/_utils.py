# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
import typing as ty

from qiskit import QuantumCircuit
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.ignis.mitigation.dd.exceptions import MissingParameter
from qiskit.providers.models import BackendProperties, BackendConfiguration
from qiskit.transpiler.passes import BasisTranslator

_units_conversion_to_seconds = {
    "ps": 10 ** -12,
    "ns": 10 ** -9,
    "us": 10 ** -6,
    "ms": 10 ** -3,
    "s": 10 ** 0,
}


def to_seconds(
    time: ty.Union[float, int],
    unit: ty.Literal["ps", "ns", "us", "ms", "s", "dt"],
    dt: ty.Optional[float] = None,
) -> float:
    """Convert a given time to seconds.

    Args:
        time: the time to convert to seconds
        unit: unit of the given time
        dt: backend dt in seconds

    Returns: the converted time in seconds
    """
    if unit == "dt":
        if dt is None:
            raise MissingParameter("dt", "to_seconds")
        return time * dt
    return _units_conversion_to_seconds[unit] * time


def to_dt_float(
    time: ty.Union[float, int],
    unit: ty.Literal["ps", "ns", "us", "ms", "s", "dt"],
    dt: float,
) -> ty.Union[float, int]:
    """Convert a given time to dt.

    Args:
        time: the time to convert to dt
        unit: unit of the given time
        dt: backend dt in seconds

    Returns: the converted time in dt, not rounded to the nearest integer
    """
    if unit == "dt":
        return time
    return _units_conversion_to_seconds[unit] * time / dt


def to_dt_rounded(
    time: ty.Union[float, int],
    unit: ty.Literal["ps", "ns", "us", "ms", "s", "dt"],
    dt: float,
) -> int:
    """Convert a given time to dt.

    Args:
        time: the time to convert to dt
        unit: unit of the given time
        dt: backend dt in seconds

    Returns: the converted time in dt
    """
    return int(to_dt_float(time, unit, dt))


def to_dt_assert_exact(
    time: ty.Union[float, int],
    unit: ty.Literal["ps", "ns", "us", "ms", "s", "dt"],
    dt: float,
    absolute_error: float = 1e-3,
) -> int:
    """Convert a given time to dt and raise an exception in case of conversion error.

    Args:
        time: the time to convert to dt
        unit: unit of the given time
        dt: backend dt in seconds
        absolute_error: maximum abs(dt_time - int(dt_time)) allowed. If this
            threshold is exceeded, an exception is raised.

    Returns: the converted time in dt

    Raises:
        RuntimeError: if the given time is not a multiple of dt within the given
            absolute error.
    """
    dt_float: float = to_dt_float(time, unit, dt)
    if abs(dt_float - int(dt_float)) > absolute_error:
        raise RuntimeError(
            f"Given time {time:.3e} {unit} is not a multiple of dt {dt:.3e} ns."
        )
    return int(dt_float)


def translate_circuit_to_basis(
    input_circuit: QuantumCircuit, configuration: BackendConfiguration
) -> QuantumCircuit:
    """Unroll the given circuit with the basis in the given configuration"""
    basis = configuration.basis_gates
    translator = BasisTranslator(SessionEquivalenceLibrary, basis)
    unrolled_dag = translator.run(circuit_to_dag(input_circuit))
    return dag_to_circuit(unrolled_dag)


def get_circuit_duration(
    input_circuit: QuantumCircuit,
    properties: BackendProperties,
    qargs: ty.Tuple[int, ...],
) -> ty.Tuple[float, str]:
    """Compute the execution time of the given circuit.

    Args:
        input_circuit: circuit to analyse
        properties: properties of the backend
        qargs: qubits on which the circuit will run on

    Returns:
        A tuple containing the execution time and the time unit used. The time unit
        used is always "s" for seconds.
    """
    dag = circuit_to_dag(input_circuit)
    durations = [0.0 for _ in range(dag.num_qubits())]

    durationless_node_names = ["measure"]

    for node in dag.topological_op_nodes():
        if node.name not in durationless_node_names:
            involved_qubits = [q.index for q in node.qargs]
            max_start_time = max(durations[i] for i in involved_qubits)
            operation_end_time = max_start_time + properties.gate_length(
                node.name, [qargs[i] for i in involved_qubits]
            )
            for qubit_index in involved_qubits:
                durations[qubit_index] = operation_end_time
    return max(durations), "s"
