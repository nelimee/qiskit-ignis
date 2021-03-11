# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
import typing as ty

from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.providers.models import BackendProperties
from qiskit.transpiler.basepasses import TransformationPass

from qiskit.ignis.mitigation.dd._utils import to_dt_assert_exact


class BarriersToDelaysPass(TransformationPass):
    def __init__(
        self,
        backend_properties: BackendProperties,
        dt: float,
        scheduling_method: str = "alap",
    ):
        """Transpiler pass to replace barriers with equivalent delays.

        This pass can be useful to replace Barrier operations with Delays such that
        the resulting circuit is exactly the same.
        Using Delay operations is useful when considering dynamical-decoupling.

        Args:
            backend_properties: properties of the backend targeted.
            dt: backend dt in seconds.
            scheduling_method: either "alap" (As Late As Possible) or "asap"
                (As Soon As Possible).

        Notes:
            Requires that the Unrolled pass has already been applied with the backend
            basis.
        """
        super(BarriersToDelaysPass, self).__init__()
        self._properties = backend_properties
        self._scheduling_method = scheduling_method
        self._dt = dt

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Apply the pass to the given DAGCircuit instance."""
        output_dag_circuit: DAGCircuit = dag._copy_circuit_metadata()
        insertion_method = DAGCircuit.apply_operation_back
        nodes = list(dag.topological_op_nodes())
        # If using ALAP scheduling, we can just reverse the circuit, do a ASAP
        # scheduling and reverse back. This is done in-place without the need to have
        # temporary DAGCircuit and reversing, by modifying how we insert in the DAG
        # and the order of the gates.
        if self._scheduling_method == "alap":
            nodes = reversed(nodes)
            insertion_method = DAGCircuit.apply_operation_front

        nqubits = dag.num_qubits()
        times_dt: ty.List[int] = [0 for _ in range(nqubits)]
        for node in nodes:
            if node.name == "barrier":
                # When we spot a barrier, we add delays to all the qubits that are late.
                max_time_dt: int = max(times_dt)
                for qubit_index, time_dt in enumerate(times_dt):
                    insertion_method(
                        output_dag_circuit,
                        Delay(max_time_dt - time_dt, unit="dt"),
                        qargs=[output_dag_circuit.qubits[qubit_index]],
                        cargs=[],
                    )
                times_dt = [max_time_dt for _ in range(nqubits)]
            elif node.name == "measure":
                insertion_method(
                    output_dag_circuit, node.op, qargs=node.qargs, cargs=node.cargs
                )
            else:
                # Else, we update the times and insert the operation
                involved_qubits_indices = [q.index for q in node.qargs]
                node_execution_time_dt = to_dt_assert_exact(
                    self._properties.gate_length(node.name, involved_qubits_indices),
                    unit="s",
                    dt=self._dt,
                )
                max_start_time_dt: int = max(
                    times_dt[i] for i in involved_qubits_indices
                )
                for qubit_index in involved_qubits_indices:
                    # If one of the qubits involved is late, insert a delay before it.
                    if times_dt[qubit_index] < max_start_time_dt:
                        time_dt: int = max_start_time_dt - times_dt[qubit_index]
                        insertion_method(
                            output_dag_circuit,
                            Delay(time_dt, unit="dt"),
                            qargs=[output_dag_circuit.qubits[qubit_index]],
                        )
                    # In any case, all the qubits involved will have the same end time.
                    times_dt[qubit_index] = max_start_time_dt + node_execution_time_dt
                # Finally, insert the operation.
                insertion_method(
                    output_dag_circuit, node.op, qargs=node.qargs, cargs=node.cargs
                )
        # Do not forget to add the remaining delays.
        max_time_dt = max(times_dt)
        for qubit_index, time_dt in enumerate(times_dt):
            insertion_method(
                output_dag_circuit,
                Delay(max_time_dt - time_dt, unit="dt"),
                qargs=[output_dag_circuit.qubits[qubit_index]],
                cargs=[],
            )
        return output_dag_circuit
