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

from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.ignis.mitigation.dd._utils import to_dt_float
from qiskit.transpiler.basepasses import TransformationPass


class MergeDelaysPass(TransformationPass):
    def __init__(self, dt: float):
        """Merge consecutive delays into one.

        Args:
            dt: backend dt in seconds
        """
        super(MergeDelaysPass, self).__init__()
        self._dt = dt

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Apply the pass to the given DAGCircuit instance."""
        output_dag_circuit: DAGCircuit = dag._copy_circuit_metadata()
        nodes = list(dag.topological_op_nodes())
        nqubits = dag.num_qubits()
        delay_times_dt_float: ty.List[float] = [0.0 for _ in range(nqubits)]

        for node in nodes:
            qubits_involved = [q.index for q in node.qargs]
            if node.name == "delay":
                # When we spot a delay, we register it to the times list
                for qubit_index in qubits_involved:
                    duration_dt_float = to_dt_float(
                        node.op.duration, node.op.unit, self._dt
                    )
                    delay_times_dt_float[qubit_index] += duration_dt_float
                # Do not add the node for the moment, we will add it to the DAG when
                # encountering the first non-delay gate on this qubit.
            else:
                # Else, we check if there is a delay waiting to be added
                for qubit_index in qubits_involved:
                    # No floating point representation issue here, we deal with the
                    # literal 0.0 so it is fine.
                    if delay_times_dt_float[qubit_index] > 0.0:
                        output_dag_circuit.apply_operation_back(
                            Delay(int(delay_times_dt_float[qubit_index]), unit="dt"),
                            qargs=[output_dag_circuit.qubits[qubit_index]],
                        )
                    delay_times_dt_float[qubit_index] = 0.0
                # In any case, add the current node
                output_dag_circuit.apply_operation_back(node.op, node.qargs, node.cargs)
        # Do not forget to add the potentially remaining delays.
        for qubit_index, time_s in enumerate(delay_times_dt_float):
            if time_s > 0.0:
                output_dag_circuit.apply_operation_back(
                    Delay(int(time_s), unit="dt"),
                    qargs=[output_dag_circuit.qubits[qubit_index]],
                )
        return output_dag_circuit
