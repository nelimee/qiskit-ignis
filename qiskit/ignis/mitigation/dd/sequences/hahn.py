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

from qiskit.providers.ibmq import IBMQBackend

from qiskit.ignis.mitigation.dd.sequences.cp import (
    CarrPurcellDynamicalDecouplingSequence,
)


class HahnSpinEchoDynamicalDecouplingSequence(CarrPurcellDynamicalDecouplingSequence):
    def __init__(self, backend: IBMQBackend, add_pre_post_rotations: bool = False):
        """Implementation of the Hahn spin echo dynamical decoupling sequence

        Args:
            backend: backend we want to use
            add_pre_post_rotations: True if a pi/2 X rotation should be added at the
                beginning and at the end of the dynamical decoupling sequence,
                else False.

        References:
            https://doi.org/10.1103/PhysRev.80.580
        """
        super(HahnSpinEchoDynamicalDecouplingSequence, self).__init__(
            backend, repetition_number=1, add_pre_post_rotations=add_pre_post_rotations
        )
