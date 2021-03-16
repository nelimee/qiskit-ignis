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

"""Flag the delays that are applied on the fundamental state |0> of the qubits."""

from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.dagcircuit import DAGCircuit

_IDENTITY_OPERATIONS = {"id", "delay", "barrier"}


class FlagFundamentalStateOperations(AnalysisPass):
    """Flag the delays that are applied on the fundamental state |0> of the qubits.

    The result is saved in ``property_set['is_applied_on_fundamental_state'][
    id(node)]`` as a boolean, for each node.
    """

    PROPERTY_SET_KEY = "is_applied_on_fundamental_state"

    def run(self, dag: DAGCircuit):
        """Run the FlagFundamentalStateOperations pass on `dag`."""
        pskey = FlagFundamentalStateOperations.PROPERTY_SET_KEY
        self.property_set[pskey] = dict()
        is_in_fundamental_state = [True for _ in range(dag.num_qubits())]
        for node in dag.topological_op_nodes():
            if node.name in _IDENTITY_OPERATIONS or node.name == "reset":
                is_applied_on_fundamental_state: bool = all(
                    is_in_fundamental_state[q.index] for q in node.qargs
                )
                self.property_set[pskey][id(node)] = is_applied_on_fundamental_state
            else:
                for q in node.qargs:
                    is_in_fundamental_state[q.index] = False
                self.property_set[pskey][id(node)] = False

            if node.name == "reset":
                for q in node.qargs:
                    is_in_fundamental_state[q.index] = True
