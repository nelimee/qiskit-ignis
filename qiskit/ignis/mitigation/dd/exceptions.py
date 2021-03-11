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

from qiskit.exceptions import QiskitError


class ComponentNotScalable(QiskitError):
    def __init__(self, component_name: str):
        super(ComponentNotScalable, self).__init__(
            f"The component '{component_name}' is not scalable."
        )


class GateNotFound(QiskitError):
    def __init__(self, gate_name: str):
        super(GateNotFound, self).__init__(
            f"The gate '{gate_name}' could not be found in the QuantumCircuit class."
        )


class MissingParameter(QiskitError):
    def __init__(self, parameter_name: str, function_name: str):
        super(MissingParameter, self).__init__(
            f"Missing parameter '{parameter_name}' in '{function_name}'."
        )
