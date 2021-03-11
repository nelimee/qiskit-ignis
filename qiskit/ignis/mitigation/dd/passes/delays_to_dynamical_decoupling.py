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

from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit
from qiskit.ignis.mitigation.dd._utils import to_dt_rounded
from qiskit.ignis.mitigation.dd.sequence import BaseDynamicalDecouplingSequence
from qiskit.providers.models import BackendProperties
from qiskit.transpiler.basepasses import TransformationPass


class DelayToDynamicalDecouplingSequencePass(TransformationPass):
    def __init__(
        self,
        dd_sequence: BaseDynamicalDecouplingSequence,
        backend_properties: BackendProperties,
        dt: float,
    ):
        """Transform the suitable Delays to dynamical decoupling sequences"""
        super(DelayToDynamicalDecouplingSequencePass, self).__init__()
        self._properties = backend_properties
        self._sequence = dd_sequence
        self._dt = dt

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Apply the pass to the given DAGCircuit instance."""
        output_dag_circuit: DAGCircuit = dag._copy_circuit_metadata()
        nodes = list(dag.topological_op_nodes())

        for node in nodes:
            if node.name == "delay":
                duration_dt: int = to_dt_rounded(
                    node.op.duration, node.op.unit, self._dt
                )
                qargs_indices = tuple(q.index for q in node.qargs)
                if self._sequence.can_be_used_on_duration(duration_dt, qargs_indices):
                    dd_circuit: QuantumCircuit = self._sequence.circuit(
                        duration_dt, qargs_indices
                    )
                    dd_dag: DAGCircuit = circuit_to_dag(dd_circuit)
                    output_dag_circuit.compose(
                        dd_dag, qubits=node.qargs, clbits=node.cargs, inplace=True
                    )
                    # Bug fix, see https://github.com/Qiskit/qiskit-terra/issues/5999
                    for gate, cal in dd_dag.calibrations.items():
                        output_dag_circuit._calibrations[gate] = cal
                else:
                    output_dag_circuit.apply_operation_back(
                        node.op, node.qargs, node.cargs
                    )
            else:
                output_dag_circuit.apply_operation_back(node.op, node.qargs, node.cargs)
        return output_dag_circuit
