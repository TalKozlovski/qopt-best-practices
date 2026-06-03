"""Tests for ParametricCommuting2qBlock that preserves parameters.

This test verifies that our modified version of Commuting2qBlock correctly
extracts and preserves parameters from input gates, unlike the original
Qiskit version which hardcodes params=[].
"""

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.converters import circuit_to_dag, dag_to_circuit

from qopt_best_practices.transpilation.parametric_commuting_2q_block import (
    ParametricCommuting2qBlock,
)


def test_parametric_commuting2q_block_preserves_single_parameter():
    """Test that a single parameter is preserved."""
    qc = QuantumCircuit(3)
    c_0 = Parameter("c_0")

    qc.rzz(c_0, 0, 1)
    qc.rzz(c_0, 1, 2)

    print("\n" + "=" * 60)
    print("Test: Single Parameter Preservation")
    print("=" * 60)
    print(f"Before: {sorted([p.name for p in qc.parameters])}")

    dag = circuit_to_dag(qc)
    nodes = list(dag.topological_op_nodes())
    block = ParametricCommuting2qBlock(nodes)

    print(f"Block params: {sorted([p.name for p in block.params])}")

    wire_order = {wire: idx for idx, wire in enumerate(dag.qubits)}
    dag.replace_block_with_op(nodes, block, wire_order)
    result = dag_to_circuit(dag)

    result_params = sorted([p.name for p in result.parameters])
    print(f"After: {result_params}")
    print("=" * 60)

    assert "c_0" in result_params, "Parameter c_0 should be preserved"
    assert len(result_params) == 1, f"Expected 1 parameter, got {len(result_params)}"


def test_parametric_commuting2q_block_preserves_two_parameters():
    """Test that two different parameters are preserved."""
    qc = QuantumCircuit(3)
    c_0 = Parameter("c_0")
    c_1 = Parameter("c_1")

    qc.rzz(c_0, 0, 1)
    qc.rzz(c_1, 1, 2)

    print("\n" + "=" * 60)
    print("Test: Two Parameters Preservation")
    print("=" * 60)
    print(f"Before: {sorted([p.name for p in qc.parameters])}")

    dag = circuit_to_dag(qc)
    nodes = list(dag.topological_op_nodes())
    block = ParametricCommuting2qBlock(nodes)

    print(f"Block params: {sorted([p.name for p in block.params])}")

    wire_order = {wire: idx for idx, wire in enumerate(dag.qubits)}
    dag.replace_block_with_op(nodes, block, wire_order)
    result = dag_to_circuit(dag)

    result_params = sorted([p.name for p in result.parameters])
    print(f"After: {result_params}")
    print("=" * 60)

    expected = {"c_0", "c_1"}
    actual = set(result_params)
    assert actual == expected, f"Expected {expected}, got {actual}"


def test_parametric_commuting2q_block_preserves_multiple_parameters():
    """Test that multiple parameters with expressions are preserved."""
    qc = QuantumCircuit(4)
    c_0 = Parameter("c_0")
    c_1 = Parameter("c_1")
    c_2 = Parameter("c_2")
    gamma = Parameter("γ[0]")

    # Each Hamiltonian term has different coefficient
    qc.rzz(c_0 * gamma, 0, 1)
    qc.rzz(c_0 * gamma, 1, 2)
    qc.rzz(c_1 * gamma, 0, 2)
    qc.rzz(c_1 * gamma, 2, 3)
    qc.rzz(c_2 * gamma, 0, 3)
    qc.rzz(c_2 * gamma, 1, 3)

    print("\n" + "=" * 60)
    print("Test: Multiple Parameters with Expressions")
    print("=" * 60)
    print(f"Before: {sorted([p.name for p in qc.parameters])}")

    dag = circuit_to_dag(qc)
    nodes = list(dag.topological_op_nodes())
    block = ParametricCommuting2qBlock(nodes)

    print(f"Block params: {sorted([p.name for p in block.params])}")

    wire_order = {wire: idx for idx, wire in enumerate(dag.qubits)}
    dag.replace_block_with_op(nodes, block, wire_order)
    result = dag_to_circuit(dag)

    result_params = sorted([p.name for p in result.parameters])
    print(f"After: {result_params}")
    print("=" * 60)

    expected = {"c_0", "c_1", "c_2", "γ[0]"}
    actual = set(result_params)
    assert actual == expected, f"Expected {expected}, got {actual}"


def test_parametric_commuting2q_block_handles_numeric_gates():
    """Test that numeric (non-parametric) gates work correctly."""
    qc = QuantumCircuit(3)

    qc.rzz(1.5, 0, 1)
    qc.rzz(2.5, 1, 2)

    print("\n" + "=" * 60)
    print("Test: Numeric Gates (No Parameters)")
    print("=" * 60)
    print(f"Before: {sorted([p.name for p in qc.parameters])}")

    dag = circuit_to_dag(qc)
    nodes = list(dag.topological_op_nodes())
    block = ParametricCommuting2qBlock(nodes)

    print(f"Block params: {sorted([p.name for p in block.params])}")

    wire_order = {wire: idx for idx, wire in enumerate(dag.qubits)}
    dag.replace_block_with_op(nodes, block, wire_order)
    result = dag_to_circuit(dag)

    result_params = sorted([p.name for p in result.parameters])
    print(f"After: {result_params}")
    print("=" * 60)

    assert len(result_params) == 0, f"Expected no parameters, got {result_params}"


def test_parametric_commuting2q_block_mixed_numeric_and_parametric():
    """Test mixed numeric and parametric gates."""
    qc = QuantumCircuit(4)
    c_0 = Parameter("c_0")
    gamma = Parameter("γ[0]")

    qc.rzz(c_0 * gamma, 0, 1)
    qc.rzz(2.5, 1, 2)
    qc.rzz(c_0 * gamma, 2, 3)

    print("\n" + "=" * 60)
    print("Test: Mixed Numeric and Parametric Gates")
    print("=" * 60)
    print(f"Before: {sorted([p.name for p in qc.parameters])}")

    dag = circuit_to_dag(qc)
    nodes = list(dag.topological_op_nodes())
    block = ParametricCommuting2qBlock(nodes)

    print(f"Block params: {sorted([p.name for p in block.params])}")

    wire_order = {wire: idx for idx, wire in enumerate(dag.qubits)}
    dag.replace_block_with_op(nodes, block, wire_order)
    result = dag_to_circuit(dag)

    result_params = sorted([p.name for p in result.parameters])
    print(f"After: {result_params}")
    print("=" * 60)

    expected = {"c_0", "γ[0]"}
    actual = set(result_params)
    assert actual == expected, f"Expected {expected}, got {actual}"


if __name__ == "__main__":
    test_parametric_commuting2q_block_preserves_single_parameter()
    test_parametric_commuting2q_block_preserves_two_parameters()
    test_parametric_commuting2q_block_preserves_multiple_parameters()
    test_parametric_commuting2q_block_handles_numeric_gates()
    test_parametric_commuting2q_block_mixed_numeric_and_parametric()
    print("\n✅ All tests passed!")

# Made with Bob
