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

from qiskit.providers.ibmq import IBMQBackend

from qiskit.ignis.mitigation.dd.components import (
    DynamicalDecouplingDelayComponent,
    DynamicalDecouplingGateComponent,
    BaseDynamicalDecouplingComponent,
)
from qiskit.ignis.mitigation.dd.sequence import BaseDynamicalDecouplingSequence


class BaseHahnSpinEchoDynamicalDecouplingSequence(BaseDynamicalDecouplingSequence):
    def __init__(
        self,
        component: BaseDynamicalDecouplingComponent,
        pre_rotation: ty.Optional[BaseDynamicalDecouplingComponent] = None,
        post_rotation: ty.Optional[BaseDynamicalDecouplingComponent] = None,
    ):
        """Base class for the Spin Echo dynamical decoupling sequence

        This class implements the Spin Echo dynamical decoupling sequence with the
        given component.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            component: the dynamical-decoupling component that will be used as pi-pulse.
            pre_rotation: pi/2 rotation at the beginning of the sequence. If not
                given, no pre-rotation is performed.
            post_rotation: pi/2 rotation at the end of the sequence. If not given,
                no post-rotation is performed.
        """
        delay = DynamicalDecouplingDelayComponent()

        sequence = [delay, component, delay]
        relative_scales = [1, None, 1]
        if pre_rotation is not None:
            sequence = [pre_rotation, *sequence]
            relative_scales = [None, *relative_scales]
        if post_rotation is not None:
            sequence = [*sequence, post_rotation]
            relative_scales = [*relative_scales, None]

        super(BaseHahnSpinEchoDynamicalDecouplingSequence, self).__init__(
            sequence=sequence, relative_scales=relative_scales
        )


class HahnSpinEchoDynamicalDecouplingSequence(
    BaseHahnSpinEchoDynamicalDecouplingSequence
):
    def __init__(self, backend: IBMQBackend, add_pre_post_rotations: bool = False):
        """Implementation of the Hahn spin echo dynamical decoupling sequence

        Args:
            backend: backend we want to use
            add_pre_post_rotations: True if a pi X rotation should be added at the
                beginning and at the end of the dynamical decoupling sequence,
                else False.

        References:
            https://doi.org/10.1103/PhysRev.80.580
        """
        configuration = backend.configuration()
        properties = backend.properties()

        x = DynamicalDecouplingGateComponent("x", configuration, properties)
        pre_rotation, post_rotation = None, None
        if add_pre_post_rotations:
            pre_rotation = DynamicalDecouplingGateComponent(
                "sx", configuration, properties
            )
            post_rotation = DynamicalDecouplingGateComponent(
                "sxdg", configuration, properties
            )

        super(HahnSpinEchoDynamicalDecouplingSequence, self).__init__(
            x, pre_rotation=pre_rotation, post_rotation=post_rotation
        )
