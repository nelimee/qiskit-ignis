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
    DynamicalDecouplingPulseComponent,
    DynamicalDecouplingGateComponent,
)
from qiskit.ignis.mitigation.dd.sequences.cp import (
    BaseCarrPurcellXPreRotationDynamicalDecouplingSequence,
)
from qiskit import pulse


class CPMGGateDynamicalDecouplingSequence(
    BaseCarrPurcellXPreRotationDynamicalDecouplingSequence
):
    def __init__(
        self,
        backend: IBMQBackend,
        repetition_number: int = 1,
        add_pre_post_rotations: bool = False,
    ):
        """Implementation of the Carr-Purcell-Meiboom-Gill dynamical decoupling sequence

        This class implements the Carr-Purcell-Meiboom-Gill dynamical decoupling
        sequence with the default Y gate from qiskit.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            backend: backend we want to use
            add_pre_post_rotations: True if a pi/2 X rotation should be added at the
                beginning and at the end of the dynamical decoupling sequence,
                else False.
            repetition_number: the number of times the pi X pulse will be repeated.
                Default to 1, i.e. Hahn Spin Echo dynamical decoupling sequence.

        References:
            https://doi.org/10.1063/1.1716296
        """
        configuration = backend.configuration()
        properties = backend.properties()

        y = DynamicalDecouplingGateComponent("y", configuration, properties)

        super(CPMGGateDynamicalDecouplingSequence, self).__init__(
            backend,
            y,
            repetition_number=repetition_number,
            add_pre_post_rotations=add_pre_post_rotations,
        )


class CPMGPulseDynamicalDecouplingSequence(
    BaseCarrPurcellXPreRotationDynamicalDecouplingSequence
):
    def __init__(
        self,
        backend: IBMQBackend,
        repetition_number: int = 1,
        add_pre_post_rotations: bool = False,
    ):
        """Implementation of the Carr-Purcell-Meiboom-Gill dynamical decoupling sequence

        This class implements the Carr-Purcell-Meiboom-Gill dynamical decoupling
        sequence with an improved Y pulse using the default X pulse.

        Args:
            backend: backend we want to use
            add_pre_post_rotations: True if a pi/2 X rotation should be added at the
                beginning and at the end of the dynamical decoupling sequence,
                else False.
            repetition_number: the number of times the pi X pulse will be repeated.
                Default to 1, i.e. Hahn Spin Echo dynamical decoupling sequence.

        References:
            https://doi.org/10.1063/1.1716296
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

        super(CPMGPulseDynamicalDecouplingSequence, self).__init__(
            backend,
            y,
            repetition_number=repetition_number,
            add_pre_post_rotations=add_pre_post_rotations,
        )
