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

import itertools as it
import typing as ty

from qiskit import QuantumCircuit
from qiskit.ignis.mitigation.dd.components import BaseDynamicalDecouplingComponent


class BaseDynamicalDecouplingSequence:
    def __init__(
        self,
        sequence: ty.Sequence[BaseDynamicalDecouplingComponent],
        relative_scales: ty.Optional[ty.Sequence[ty.Optional[float]]] = None,
    ):
        """The base sequence of components representing a dynamical decoupling scheme.

        The goal of this class if to provide a generic mechanism to build dynamical
        decoupling sequences with as much liberty as possible.
        This class will then be used to create actual dynamical decoupling scheme,
        without having to re-implement all the logic.

        Args:
            sequence: a sequence of dynamical decoupling elements created by the user.
            relative_scales: a sequence of elements that can be either floats or None
                representing the relative scales between the different components in
                the given sequence. Several pre-conditions need to be enforced:
                1. The relative_scales sequence contains at least as much elements as
                   the sequence parameter.
                2. The relative scale of a non scalable component should be None.
                3. The relative scale of a scalable component should be a positive
                   float.
                Default to equal relative scales, i.e. None when the related
                component is not scalable and 1 when it is scalable.
        """
        self._sequence = list()
        self._relative_scales = list()

        for comp, scale in zip(sequence, relative_scales or it.repeat(None)):
            self._add_component(comp, scale)

    def _add_component(
        self,
        component: BaseDynamicalDecouplingComponent,
        relative_scale: ty.Optional[float] = None,
    ) -> None:
        """Add a component and its relative scale to the sequence"""
        self._sequence.append(component)
        if component.is_scalable:
            if relative_scale is None:
                self._relative_scales.append(1)
            else:
                self._relative_scales.append(relative_scale)
        else:
            self._relative_scales.append(None)

    def can_be_used_on_duration(
        self, duration_dt: int, qargs: ty.Tuple[int, ...]
    ) -> bool:
        """Check if the sequence can be used on a delay of the given duration

        Args:
            duration_dt: the duration of the delay encountered in dt unit.
            qargs: quantum arguments, namely quantum register indices the sequence
                should be applied on to test.

        Returns:
            True if the sequence can replace the delay, else False.
        """
        fixed_duration_dt: int = sum(
            component.duration(qargs)
            for component in self._sequence
            if not component.is_scalable
        )
        return duration_dt > fixed_duration_dt

    def circuit(
        self,
        total_duration_dt: int,
        qargs: ty.Tuple[int, ...],
    ) -> QuantumCircuit:
        """
        Build the QuantumCircuit instance that implement the dynamical decoupling scheme

        Args:
            total_duration_dt: total duration in dt of the returned circuit
            qargs: the hardware qubits the dynamical decoupling scheme should be
                applied on
        Returns:
            Returns a QuantumCircuit instance of the specified duration that implement
            the dynamical decoupling scheme represented by the instance.
        """
        total_scale: float = sum(sc for sc in self._relative_scales if sc is not None)
        fixed_duration_dt: int = sum(
            component.duration(qargs)
            for component in self._sequence
            if not component.is_scalable
        )
        duration_to_scale_dt: float = total_duration_dt - fixed_duration_dt

        circuit = QuantumCircuit(1)
        for component, relative_scale in zip(self._sequence, self._relative_scales):
            if component.is_scalable:
                component_duration_dt = round(
                    duration_to_scale_dt * relative_scale / total_scale
                )
                component.scale_to(component_duration_dt).apply(circuit, qargs, [0])
            else:
                component.apply(circuit, qargs, [0])

        return circuit
