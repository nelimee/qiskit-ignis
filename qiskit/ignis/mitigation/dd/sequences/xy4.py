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
import typing as ty

from qiskit.providers.ibmq import IBMQBackend

from qiskit.ignis.mitigation.dd.sequence import BaseDynamicalDecouplingSequence
from qiskit.ignis.mitigation.dd.components import (
    DynamicalDecouplingGateComponent,
    DynamicalDecouplingDelayComponent,
    DynamicalDecouplingPulseComponent,
    BaseDynamicalDecouplingComponent,
)
from qiskit import pulse


class BaseXY4DynamicalDecouplingSequence(BaseDynamicalDecouplingSequence):
    def __init__(
        self,
        X: ty.Union[
            BaseDynamicalDecouplingComponent, ty.List[BaseDynamicalDecouplingComponent]
        ],
        Y: ty.Union[
            BaseDynamicalDecouplingComponent, ty.List[BaseDynamicalDecouplingComponent]
        ],
        symmetric: bool = True,
        x_scales: ty.Optional[ty.List[float]] = None,
        y_scales: ty.Optional[ty.List[float]] = None,
    ):
        """Implementation of the XY-4 dynamical decoupling sequence

        The XY-4 dynamical decoupling sequence is either
            tau/2 - X - tau - Y - tau - X - tau - Y - tau/2
        for the symmetric version or
            tau - X - tau - Y - tau - X - tau - Y
        for the non-symmetric one.

        Args:
            X: first component (or list of components) to use as a X gate
            Y: second component (or list of components) to use as a Y gate
            x_scales: list of scales for the delays in the given X. Required to have
                the same length as X if X is a list of BaseDynamicalDecouplingComponent.
            y_scales: list of scales for the delays in the given Y. Required to have
                the same length as Y if Y is a list of BaseDynamicalDecouplingComponent.
            symmetric: if True, use the symmetric version of the XY-4 dynamical
                decoupling scheme. Else, use the non-symmetric version
        """
        if isinstance(X, BaseDynamicalDecouplingComponent):
            X = [X]
            x_scales = [x_scales]
        else:
            assert len(X) == len(x_scales)
        if isinstance(Y, BaseDynamicalDecouplingComponent):
            Y = [Y]
            y_scales = [y_scales]
        else:
            assert len(Y) == len(y_scales)

        delay = DynamicalDecouplingDelayComponent()

        if symmetric:
            super(BaseXY4DynamicalDecouplingSequence, self).__init__(
                [delay, *X, delay, *Y, delay, *X, delay, *Y, delay],
                [1 / 2, *x_scales, 1, *y_scales, 1, *x_scales, 1, *y_scales, 1 / 2],
            )
        else:
            super(BaseXY4DynamicalDecouplingSequence, self).__init__(
                [delay, *X, delay, *Y, delay, *X, delay, *Y],
                [1, *x_scales, 1, *y_scales, 1, *x_scales, 1, *y_scales],
            )


class XY4DynamicalDecouplingSequence(BaseXY4DynamicalDecouplingSequence):
    def __init__(
        self,
        backend: IBMQBackend,
        symmetric: bool = True,
    ):
        """Implementation of the XY-4 dynamical decoupling sequence

        The XY-4 dynamical decoupling sequence is either
            tau/2 - X - tau - Y - tau - X - tau - Y - tau/2
        for the symmetric version or
            tau - X - tau - Y - tau - X - tau - Y
        for the non-symmetric one.

        Args:
            backend: backend we want to use
            symmetric: if True, use the symmetric version of the XY-4 dynamical
                decoupling scheme. Else, use the non-symmetric version.
        """
        configuration = backend.configuration()
        properties = backend.properties()
        X = DynamicalDecouplingGateComponent("x", configuration, properties)
        Y = DynamicalDecouplingGateComponent("y", configuration, properties)

        super(XY4DynamicalDecouplingSequence, self).__init__(X, Y, symmetric)


class XY4PulseDynamicalDecouplingSequence(BaseXY4DynamicalDecouplingSequence):
    def __init__(
        self,
        backend: IBMQBackend,
        symmetric: bool = True,
    ):
        """Implementation of the XY-4 dynamical decoupling sequence

        The XY-4 dynamical decoupling sequence is either
            tau/2 - X - tau - Y - tau - X - tau - Y - tau/2
        for the symmetric version or
            tau - X - tau - Y - tau - X - tau - Y
        for the non-symmetric one.

        Notes:
            This implementation replaces the default pulse sequence for the Y gate
            with an optimised pulse sequence, using the same pulse as for the X gate.
            Y gate is implemented as
                Rz(pi/2) X Rz(-pi/2)
            instead of
                Rz(pi/2) sqrt(X) Rz(2*pi) sqrt(X) Rz(-pi/2)
            when using the default Y gate pulses.

        Args:
            backend: backend we want to apply the dynamical decoupling sequence to
            symmetric: if True, use the symmetric version of the XY-4 dynamical
                decoupling scheme. Else, use the non-symmetric version.
        """
        configuration = backend.configuration()
        properties = backend.properties()
        defaults = backend.defaults()
        ism = defaults.instruction_schedule_map

        calibrations = dict()
        for qubit_index in range(configuration.num_qubits):
            with pulse.build(backend, name="y_gate") as y_gate_schedule:
                channel = pulse.DriveChannel(qubit_index)
                pulse.shift_phase(pi / 2, channel)
                pulse.call(ism.get("x", [qubit_index]))
                pulse.shift_phase(-pi / 2, channel)

            calibrations[(qubit_index,)] = deepcopy(y_gate_schedule)

        X = DynamicalDecouplingGateComponent("x", configuration, properties)
        Y = DynamicalDecouplingPulseComponent("y", calibrations)

        super(XY4PulseDynamicalDecouplingSequence, self).__init__(X, Y, symmetric)
