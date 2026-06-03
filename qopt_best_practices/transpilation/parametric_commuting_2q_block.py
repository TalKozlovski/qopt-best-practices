"""Parametric version of Commuting2qBlock that preserves parameters.

This module provides a modified version of Qiskit's Commuting2qBlock that
extracts and preserves parameters from input gates instead of discarding them.
"""

from __future__ import annotations

from collections.abc import Iterable

from qiskit.circuit import Gate, Qubit, Clbit
from qiskit.circuit.parameterexpression import ParameterExpression
from qiskit.dagcircuit import DAGOpNode
from qiskit.exceptions import QiskitError
from qiskit.transpiler.passes.routing.commuting_2q_gate_routing.commuting_2q_block import (
    Commuting2qBlock,
)


class ParametricCommuting2qBlock(Commuting2qBlock):
    """A gate made of commuting two-qubit gates that preserves parameters.

    This is a modified version of Qiskit's Commuting2qBlock that extracts
    and preserves parameters from the input gates instead of discarding them.

    The original Commuting2qBlock hardcodes params=[] which causes all
    parametric information to be lost. This version collects all unique
    parameters from the input gates and passes them to the Gate constructor.

    This is intended for use with commuting swap strategies to make it convenient
    for the swap strategy router to identify which blocks of operations commute,
    while preserving parametric structure for optimization.
    """

    def __init__(self, node_block: Iterable[DAGOpNode]) -> None:
        """
        Args:
            node_block: A block of nodes that commute.

        Raises:
            QiskitError: If the nodes in the node block do not apply to two-qubits.
        """
        qubits: set[Qubit] = set()
        cbits: set[Clbit] = set()
        all_params: set = set()

        for node in node_block:
            if len(node.qargs) != 2:
                raise QiskitError(f"Node {node.name} does not apply to two-qubits.")

            qubits.update(node.qargs)
            cbits.update(node.cargs)

            # Extract parameters from this node's operation
            if hasattr(node.op, "params"):
                for param in node.op.params:
                    if isinstance(param, ParameterExpression):
                        # Add all free parameters from this expression
                        all_params.update(param.parameters)
                    # Note: numeric params don't need to be tracked as Parameters

        if cbits:
            raise QiskitError(
                f"{self.__class__.__name__} does not accept nodes with classical bits."
            )

        # Convert set to list for params argument
        params_list = list(all_params)

        # Call Gate.__init__ directly to bypass Commuting2qBlock.__init__
        # which hardcodes params=[]
        Gate.__init__(
            self,
            "parametric_commuting_2q_block",
            num_qubits=len(qubits),
            params=params_list,
            label="Parametric Commuting 2q gates",
        )
        self.node_block = node_block
        self.qubits = qubits

    def __iter__(self):
        """Iterate through the nodes in the block."""
        return iter(self.node_block)

# Made with Bob

