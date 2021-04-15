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
from math import sin, pi
from copy import deepcopy

from qiskit.providers.ibmq import IBMQBackend

from qiskit.ignis.mitigation.dd.components import (
    DynamicalDecouplingDelayComponent,
    DynamicalDecouplingGateComponent,
    BaseDynamicalDecouplingComponent,
    DynamicalDecouplingPulseComponent,
)
from qiskit.ignis.mitigation.dd.sequence import BaseDynamicalDecouplingSequence
from qiskit import pulse


class BaseUhrigDynamicalDecouplingSequence(BaseDynamicalDecouplingSequence):
    def __init__(
        self,
        component: BaseDynamicalDecouplingComponent,
        pre_rotation: ty.Optional[BaseDynamicalDecouplingComponent] = None,
        post_rotation: ty.Optional[BaseDynamicalDecouplingComponent] = None,
        repetition_number: int = 1,
    ):
        """Base class for the Uhrig dynamical decoupling sequence

        This class implements the Uhrig dynamical decoupling sequence with the
        given component.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            component: the dynamical-decoupling component that will be used as pi-pulse.
                Y gate for the Uhrig dynamical decoupling sequence.
            pre_rotation: pi/2 rotation at the beginning of the sequence. If not
                given, no pre-rotation is performed.
            post_rotation: pi/2 rotation at the end of the sequence. If not given,
                no post-rotation is performed.
            repetition_number: the number of times the component will be repeated.
                Default to 1.
        """
        delay = DynamicalDecouplingDelayComponent()

        if repetition_number == 1:
            sequence = [delay, component, delay]
            relative_scales = [1, None, 1]
        else:
            offsets = [
                sin(pi * i / (2 * repetition_number)) ** 2
                for i in range(repetition_number + 1)
            ]
            offsets_scales = [
                offsets[i + 1] - offsets[i] for i in range(repetition_number)
            ]

            sequence = [delay]
            relative_scales = [offsets_scales[0]]
            for i in range(1, repetition_number):
                sequence.extend([component, delay])
                relative_scales.extend([None, offsets_scales[i]])

        if pre_rotation is not None:
            sequence = [pre_rotation, *sequence]
            relative_scales = [None, *relative_scales]
        if post_rotation is not None:
            sequence = [*sequence, post_rotation]
            relative_scales = [*relative_scales, None]

        super(BaseUhrigDynamicalDecouplingSequence, self).__init__(
            sequence=sequence, relative_scales=relative_scales
        )


class BaseUhrigXPreRotationDynamicalDecouplingSequence(
    BaseUhrigDynamicalDecouplingSequence
):
    def __init__(
        self,
        backend: IBMQBackend,
        component: BaseDynamicalDecouplingComponent,
        repetition_number: int = 1,
        add_pre_post_rotations: bool = False,
    ):
        """Base class for the Uhrig dynamical decoupling sequence

        This class implements the Uhrig dynamical decoupling sequence with the
        given component.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            backend: backend we want to use
            component: the dynamical-decoupling component that will be used as pi-pulse.
                Y gate for the Uhrig dynamical decoupling sequence.
            repetition_number: the number of times the component will be repeated.
                Default to 1.
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

        super(BaseUhrigXPreRotationDynamicalDecouplingSequence, self).__init__(
            component,
            pre_rotation=pre_rotation,
            post_rotation=post_rotation,
            repetition_number=repetition_number,
        )


class UhrigGateDynamicalDecouplingSequence(
    BaseUhrigXPreRotationDynamicalDecouplingSequence
):
    def __init__(
        self,
        backend: IBMQBackend,
        repetition_number: int = 1,
        add_pre_post_rotations: bool = False,
    ):
        """Implementation of the Uhrig dynamical decoupling sequence

        This class implements the Uhrig dynamical decoupling sequence with the
        default Y gate from qiskit.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            backend: backend we want to use
            add_pre_post_rotations: True if a pi/2 X rotation should be added at the
                beginning and at the end of the dynamical decoupling sequence,
                else False.
            repetition_number: the number of times the pi Y pulse will be repeated.
                Default to 1.
        """
        configuration = backend.configuration()
        properties = backend.properties()

        y = DynamicalDecouplingGateComponent("y", configuration, properties)

        super(UhrigGateDynamicalDecouplingSequence, self).__init__(
            backend,
            y,
            repetition_number=repetition_number,
            add_pre_post_rotations=add_pre_post_rotations,
        )


class UhrigPulseDynamicalDecouplingSequence(
    BaseUhrigXPreRotationDynamicalDecouplingSequence
):
    def __init__(
        self,
        backend: IBMQBackend,
        repetition_number: int = 1,
        add_pre_post_rotations: bool = False,
    ):
        """Implementation of the Uhrig dynamical decoupling sequence

        This class implements the Uhrig dynamical decoupling sequence with the
        default Y gate from qiskit.

        Notes:
            The state this sequence is applied on should be in the XY plane.

        Args:
            backend: backend we want to use
            add_pre_post_rotations: True if a pi/2 X rotation should be added at the
                beginning and at the end of the dynamical decoupling sequence,
                else False.
            repetition_number: the number of times the pi Y pulse will be repeated.
                Default to 1.
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

        super(UhrigPulseDynamicalDecouplingSequence, self).__init__(
            backend,
            y,
            repetition_number=repetition_number,
            add_pre_post_rotations=add_pre_post_rotations,
        )
