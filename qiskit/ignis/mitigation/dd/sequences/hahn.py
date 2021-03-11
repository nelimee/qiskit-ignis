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

from copy import deepcopy
from math import pi

from qiskit.providers.ibmq import IBMQBackend

from qiskit.ignis.mitigation.dd.components import (
    DynamicalDecouplingDelayComponent,
    DynamicalDecouplingPulseComponent,
)
from qiskit.ignis.mitigation.dd.sequence import BaseDynamicalDecouplingSequence
from qiskit import pulse


class HahnSpinEchoDynamicalDecouplingSequence(BaseDynamicalDecouplingSequence):
    def __init__(
        self,
        backend: IBMQBackend,
    ):
        """Implementation of the Hahn spin echo dynamical decoupling sequence

        Args:
            backend: backend we want to use
        """
        configuration = backend.configuration()
        defaults = backend.defaults()
        ism = defaults.instruction_schedule_map

        y_calibrations = dict()
        for qubit_index in range(configuration.num_qubits):
            default_x_calibration = ism.get("x", [qubit_index])
            channel = pulse.DriveChannel(qubit_index)

            with pulse.build(backend, name="y_gate") as y_gate:
                pulse.shift_phase(pi / 2, channel)
                pulse.call(default_x_calibration)
                pulse.shift_phase(-pi / 2, channel)

            y_calibrations[(qubit_index,)] = deepcopy(y_gate)

        y = DynamicalDecouplingPulseComponent("y", y_calibrations)
        delay = DynamicalDecouplingDelayComponent()

        super(HahnSpinEchoDynamicalDecouplingSequence, self).__init__(
            sequence=[delay, y, delay], relative_scales=[1, None, 1]
        )
