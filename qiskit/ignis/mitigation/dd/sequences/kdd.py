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
from qiskit.ignis.mitigation.dd.sequences.xy4 import BaseXY4DynamicalDecouplingSequence
from qiskit import pulse


class XY4KDDDynamicalDecouplingSequence(BaseXY4DynamicalDecouplingSequence):
    def __init__(
        self,
        backend: IBMQBackend,
        symmetric: bool = True,
    ):
        """Implementation of the KDD dynamical decoupling sequence

        The KDD dynamical decoupling sequence is inspired from

            Levitt, M. H. 1996 Composite pulses. In Encyclopedia of nuclear magnetic
            resonance (eds D. M. Grant & R. K. Harris), pp. 1396–1411. New York, NY:
            Wiley.

        and consists in a self-correcting sequence KDD that implement a robust pi-pulse
        with respect to a given axis P as:

            Rz(pi/6) P Rz(-pi/6) P Rz(pi/2) P Rz(-pi/2) P Rz(pi/6) P Rz(-pi/6) Rz(-pi/3)

        The dynamical decoupling scheme is then obtained by inserting delays between
        each P gate (Rz being a phase shift, i.e. free on IBM hardware, it can be
        ignored) and then use the formula:

            KDD(0) KDD(pi/2) KDD(0) KDD(pi/2)

        where KDD(a) means that we execute the KDD sequence with a global phase shift
        of angle a.

        More succinctly, the decoupling scheme implemented here is a XY-4 decoupling
        scheme with robust implementations of X and Y.

        Args:
            backend: backend we want to use
            symmetric: if True, use the symmetric version of the XY-4 dynamical
                decoupling scheme. Else, use the non-symmetric version.
        """
        configuration = backend.configuration()
        defaults = backend.defaults()
        ism = defaults.instruction_schedule_map

        calibrations = {
            "x_pi_6": dict(),
            "x_pi_2": dict(),
            "x": dict(),
            "rz_-3": dict(),
            "rz_2": dict(),
            "rz_-2": dict(),
        }
        for qubit_index in range(configuration.num_qubits):
            default_x_calibration = ism.get("x", [qubit_index])
            channel = pulse.DriveChannel(qubit_index)

            with pulse.build(backend, name="x_pi_6") as x_pi_6_schedule:
                pulse.shift_phase(pi / 6, channel)
                pulse.call(default_x_calibration)
                pulse.shift_phase(-pi / 6, channel)
            with pulse.build(backend, name="x_pi_2") as x_pi_2_schedule:
                pulse.shift_phase(pi / 2, channel)
                pulse.call(default_x_calibration)
                pulse.shift_phase(-pi / 2, channel)
            with pulse.build(backend, name="rz_-3") as rz_m3_schedule:
                pulse.shift_phase(-pi / 3, channel)
            with pulse.build(backend, name="rz_-2") as rz_m2_schedule:
                pulse.shift_phase(-pi / 2, channel)
            with pulse.build(backend, name="rz_2") as rz_2_schedule:
                pulse.shift_phase(pi / 2, channel)

            calibrations["x_pi_6"][(qubit_index,)] = deepcopy(x_pi_6_schedule)
            calibrations["x_pi_2"][(qubit_index,)] = deepcopy(x_pi_2_schedule)
            calibrations["x"][(qubit_index,)] = deepcopy(default_x_calibration)
            calibrations["rz_2"][(qubit_index,)] = deepcopy(rz_2_schedule)
            calibrations["rz_-2"][(qubit_index,)] = deepcopy(rz_m2_schedule)
            calibrations["rz_-3"][(qubit_index,)] = deepcopy(rz_m3_schedule)

        x_pi_6 = DynamicalDecouplingPulseComponent("x_pi_6", calibrations["x_pi_6"])
        x_pi_2 = DynamicalDecouplingPulseComponent("x_pi_2", calibrations["x_pi_2"])
        x = DynamicalDecouplingPulseComponent("x", calibrations["x"])
        rz_2 = DynamicalDecouplingPulseComponent("rz_2", calibrations["rz_2"])
        rz_m2 = DynamicalDecouplingPulseComponent("rz_-2", calibrations["rz_-2"])
        rz_m3 = DynamicalDecouplingPulseComponent("rz_-3", calibrations["rz_-3"])
        delay = DynamicalDecouplingDelayComponent()

        base_x = [x_pi_6, delay, x, delay, x_pi_2, delay, x, delay, x_pi_6, rz_m3]
        base_x_scales = [None, 1, None, 1, None, 1, None, 1, None, None]
        super(XY4KDDDynamicalDecouplingSequence, self).__init__(
            X=[delay, *base_x, delay],
            Y=[delay, rz_2, *base_x, rz_m2, delay],
            symmetric=symmetric,
            x_scales=[1 / 2, *base_x_scales, 1 / 2],
            y_scales=[1 / 2, None, *base_x_scales, None, 1 / 2],
        )
