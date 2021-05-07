# This code is part of qiskit-runtime.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""The FeatureMap class."""

import numpy as np
import json

import numpy as np

from qiskit import QuantumCircuit, QuantumRegister


class FeatureMap:
    """Mapping data with the feature map."""

    def __init__(self, feature_dimension, entangler_map=None):
        """FeatureMap constructor.

        Args:
            feature_dimension (int): Number of features (twice the number of
                qubits for this encoding).
            entangler_map (list[list]): Connectivity of qubits with a list of [source, target],
                or None for full entanglement.
                Note that the order in the list is the order of applying the two-qubit gate.

        Raises:
            ValueError: If an input value is invalid.
        """

        if isinstance(feature_dimension, int):
            if feature_dimension % 2 == 0:
                self._feature_dimension = feature_dimension
            else:
                raise ValueError('Feature dimension must be an even integer.')
        else:
            raise ValueError('Feature dimension must be an even integer.')

        self._num_qubits = int(feature_dimension/2)

        if entangler_map is None:
            self._entangler_map = [[i, j] for i in range(self._num_qubits) \
                                   for j in range(i + 1, self._num_qubits)]
        else:
            self._entangler_map = entangler_map

        self._num_parameters = self._num_qubits

    def construct_circuit(self, x=None, parameters=None, q=None, inverse=False, name=None):
        """Construct the feature map circuit.

        Args:
            x (numpy.ndarray): Data vector of size feature_dimension.
            parameters (numpy.ndarray): Optional parameters in feature map.
            q (QauntumRegister): The QuantumRegister object for the circuit.
            inverse (bool): Whether or not to invert the circuit.
            name (str): The name of the quantum circuit. If not set, an
                automatically generated string will be assigned.

        Returns:
            QuantumCircuit: A quantum circuit transforming data x.

        Raises:
            ValueError: If an input value is invalid.
        """

        if parameters is not None:
            if isinstance(parameters, (int, float)):
                raise ValueError('Parameters must be a list.')
            if len(parameters) == 1:
                parameters = parameters * np.ones(self._num_qubits)
            else:
                if len(parameters) != self._num_parameters:
                    raise ValueError(
                        f"The number of feature map parameters must be {self._num_parameters}.")

        if len(x) != self._feature_dimension:
            raise ValueError(f"The input vector must be of length {self._feature_dimension}.")

        if q is None:
            q = QuantumRegister(self._num_qubits, name='q')

        circuit = QuantumCircuit(q, name=name)

        for i in range(self._num_qubits):
            circuit.ry(-parameters[i], q[i])

        for source, target in self._entangler_map:
            circuit.cz(q[source], q[target])

        for i in range(self._num_qubits):
            circuit.rz(-2*x[2*i+1], q[i])
            circuit.rx(-2*x[2*i], q[i])

        if inverse:
            return circuit.inverse()
        return circuit

    def to_json(self):
        """Return JSON representation of this object.

        Returns:
            str: JSON string representing this object.
        """
        return json.dumps(
            {'feature_dimension': self._feature_dimension,
             'entangler_map': self._entangler_map})

    @classmethod
    def from_json(cls, data):
        """Return an instance of this class from the JSON representation.

        Args:
            data (str): JSON string representing an object.

        Returns:
            FeatureMap: An instance of this class.
        """
        return cls(**json.loads(data))
