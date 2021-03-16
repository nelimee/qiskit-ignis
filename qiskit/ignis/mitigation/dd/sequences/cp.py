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


class BaseCarrPurcellDynamicalDecouplingSequence(BaseDynamicalDecouplingSequence):
    def __init__(
        self,
        component: BaseDynamicalDecouplingComponent,
        pre_rotation: ty.Optional[BaseDynamicalDecouplingComponent] = None,
        post_rotation: ty.Optional[BaseDynamicalDecouplingComponent] = None,
        repetition_number: int = 1,
    ):
        """Base class for the Carr-Purcell dynamical decoupling sequence

        This class implements the Carr-Purcell dynamical decoupling sequence with the
        given component.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            component: the dynamical-decoupling component that will be used as pi-pulse.
                X gate for the Carr-Purcell dynamical decoupling sequence, Y gate for
                the Carr-Purcell-Meiboom-Gill sequence for example.
            pre_rotation: pi/2 rotation at the beginning of the sequence. If not
                given, no pre-rotation is performed.
            post_rotation: pi/2 rotation at the end of the sequence. If not given,
                no post-rotation is performed.
            repetition_number: the number of times the component will be repeated.
                Default to 1, i.e. Hahn Spin Echo dynamical decoupling sequence.
        """
        delay = DynamicalDecouplingDelayComponent()

        sequence = [delay] + [component, delay] * repetition_number
        relative_scales = [1] + [None, 1] * repetition_number
        if pre_rotation is not None:
            sequence = [pre_rotation, *sequence]
            relative_scales = [None, *relative_scales]
        if post_rotation is not None:
            sequence = [*sequence, post_rotation]
            relative_scales = [*relative_scales, None]

        super(BaseCarrPurcellDynamicalDecouplingSequence, self).__init__(
            sequence=sequence, relative_scales=relative_scales
        )


class BaseCarrPurcellXPreRotationDynamicalDecouplingSequence(
    BaseCarrPurcellDynamicalDecouplingSequence
):
    def __init__(
        self,
        backend: IBMQBackend,
        component: BaseDynamicalDecouplingComponent,
        repetition_number: int = 1,
        add_pre_post_rotations: bool = False,
    ):
        """Base class for the Carr-Purcell dynamical decoupling sequence

        This class implements the Carr-Purcell dynamical decoupling sequence with the
        given component.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            backend: backend we want to use
            component: the dynamical-decoupling component that will be used as pi-pulse.
                X gate for the Carr-Purcell dynamical decoupling sequence, Y gate for
                the Carr-Purcell-Meiboom-Gill sequence for example.
            repetition_number: the number of times the component will be repeated.
                Default to 1, i.e. Hahn Spin Echo dynamical decoupling sequence.
            add_pre_post_rotations: True if a pi/2 X rotation should be added at the
                beginning and at the end of the dynamical decoupling sequence,
                else False.
        """
        configuration = backend.configuration()
        properties = backend.properties()

        pre_rotation, post_rotation = None, None
        if add_pre_post_rotations:
            pre_rotation = DynamicalDecouplingGateComponent(
                "sx", configuration, properties
            )
            post_rotation = DynamicalDecouplingGateComponent(
                "sxdg", configuration, properties
            )

        super(BaseCarrPurcellXPreRotationDynamicalDecouplingSequence, self).__init__(
            component,
            pre_rotation=pre_rotation,
            post_rotation=post_rotation,
            repetition_number=repetition_number,
        )


class CarrPurcellDynamicalDecouplingSequence(
    BaseCarrPurcellXPreRotationDynamicalDecouplingSequence
):
    def __init__(
        self,
        backend: IBMQBackend,
        repetition_number: int = 1,
        add_pre_post_rotations: bool = False,
    ):
        """Implementation of the Carr-Purcell dynamical decoupling sequence

        This class implements the Carr-Purcell dynamical decoupling sequence with the
        default X gate from qiskit.

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
            https://doi.org/10.1103/PhysRev.94.630
        """
        configuration = backend.configuration()
        properties = backend.properties()

        x = DynamicalDecouplingGateComponent("x", configuration, properties)

        super(CarrPurcellDynamicalDecouplingSequence, self).__init__(
            backend,
            x,
            repetition_number=repetition_number,
            add_pre_post_rotations=add_pre_post_rotations,
        )
