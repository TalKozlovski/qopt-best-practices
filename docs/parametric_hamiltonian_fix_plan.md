# Plan: Fix Parameter Loss Bug in SAT Mapping for Parametric Hamiltonians

## Executive Summary

**Problem**: When using `annotated_qaoa_ansatz()` with parametric Hamiltonians that have identical graph structures, the `AnnotatedPrepareCostLayer` transpilation pass incorrectly merges or eliminates parametric weight coefficients.

**Solution**: Modify `AnnotatedPrepareCostLayer` to group `rzz` gates by their parametric expression signature, not just by qubit pairs. This preserves all parametric coefficients while still allowing optimization for numeric gates.

## Current Understanding

### How the Bug Occurs

1. **Input**: Parametric Hamiltonian `H = c_0*H_0 + c_1*H_1 + c_2*H_2` where all H_i have identical graph structure
2. **After `annotated_qaoa_ansatz()`**: Circuit has parameters `[c_0, c_1, c_2, β[0], γ[0]]`
3. **In `AnnotatedPrepareCostLayer.run()`** (line 67):
   - All `rzz` gates are collected into `commuting_nodes`
   - `Commuting2qBlock(commuting_nodes)` is created
   - **BUG**: When multiple `rzz` gates operate on the same qubit pairs but with different parametric coefficients (e.g., `c_0*γ`, `c_1*γ`, `c_2*γ`), they get merged
   - Result: Only one parameter survives (typically `c_2`)
4. **Output**: Parameters `[c_2, β[0], γ[0]]` - lost `c_0` and `c_1`

### Root Cause

The `Commuting2qBlock` class (from Qiskit) is designed for circuit optimization. It assumes that multiple gates on the same qubits can be combined:
- ✅ Correct for numeric: `Rzz(0.5, [0,1])` + `Rzz(0.3, [0,1])` → `Rzz(0.8, [0,1])`
- ❌ Incorrect for parametric: `Rzz(c_0*γ, [0,1])` + `Rzz(c_1*γ, [0,1])` should NOT be merged

The pass doesn't distinguish between:
- **Numeric optimization**: Combining numeric coefficients
- **Parametric preservation**: Keeping independent parametric coefficients separate

## Solution Design: Option 1 (Recommended)

### Approach

Modify `AnnotatedPrepareCostLayer.run()` to group `rzz` gates by their **parametric signature** before creating `Commuting2qBlock` instances.

### Key Concept: Parametric Signature

A parametric signature uniquely identifies the parametric expression structure:
- `c_0 * γ[0]` → signature: `"c_0*γ[0]"` or hash of expression
- `c_1 * γ[0]` → signature: `"c_1*γ[0]"` or hash of expression  
- `c_2 * γ[0]` → signature: `"c_2*γ[0]"` or hash of expression
- `0.5` (numeric) → signature: `"numeric"` (all numeric gates can be grouped together)

### Implementation Strategy

```python
# In AnnotatedPrepareCostLayer.run(), replace lines 53-75 with:

commuting_nodes = []
rz_gates = []
for box_node in box_dag.topological_op_nodes():
    if box_node.op.name == "rzz":
        commuting_nodes.append(box_node)
    elif box_node.op.name == "rz":
        rz_gates.append(box_node)
        box_dag.remove_op_node(box_node)
    else:
        raise ValueError(...)

# NEW: Group rzz gates by parametric signature
param_groups = _group_by_parametric_signature(commuting_nodes)

# Create separate Commuting2qBlock for each parametric group
wire_order = {wire: idx for idx, wire in enumerate(box_dag.qubits) 
              if wire not in box_dag.idle_wires()}

for param_sig, nodes in param_groups.items():
    commuting_block = Commuting2qBlock(nodes)
    box_dag.replace_block_with_op(nodes, commuting_block, wire_order)

# Re-add rz gates
for z_node in rz_gates:
    box_dag.apply_operation_back(z_node.op, qargs=z_node.qargs, cargs=z_node.cargs)
```

### Helper Function

```python
def _group_by_parametric_signature(nodes):
    """Group nodes by their parametric signature.
    
    Nodes with the same parametric expression structure are grouped together.
    All numeric (non-parametric) nodes are grouped together.
    
    Args:
        nodes: List of DAGOpNode objects with rzz gates
        
    Returns:
        dict: Mapping from parametric signature to list of nodes
    """
    from collections import defaultdict
    from qiskit.circuit.parameterexpression import ParameterExpression
    
    groups = defaultdict(list)
    
    for node in nodes:
        # Get the parameter (angle) of the rzz gate
        param = node.op.params[0]
        
        if isinstance(param, ParameterExpression):
            # For parametric gates, use the string representation as signature
            # This ensures gates with different parameters are kept separate
            signature = str(param)
        else:
            # All numeric gates can be grouped together
            signature = "numeric"
        
        groups[signature].append(node)
    
    return groups
```

### Why This Works

1. **Preserves parametric coefficients**: Gates with `c_0*γ`, `c_1*γ`, `c_2*γ` get different signatures → separate blocks → parameters preserved
2. **Allows numeric optimization**: All numeric gates share signature `"numeric"` → single block → can be optimized
3. **Minimal code change**: Only modifies `AnnotatedPrepareCostLayer.run()`, no changes to `Commuting2qBlock`
4. **Backward compatible**: Existing numeric workflows unchanged

## Implementation Plan

### Phase 1: Understand and Verify (Current)
- [x] Analyze the bug report and understand the issue
- [x] Read relevant code in `AnnotatedPrepareCostLayer`
- [ ] Create minimal reproduction test case
- [ ] Verify bug exists in current code

### Phase 2: Implement Fix
- [ ] Add `_group_by_parametric_signature()` helper function
- [ ] Modify `AnnotatedPrepareCostLayer.run()` to use parametric grouping
- [ ] Handle edge cases (empty groups, single-node groups, etc.)

### Phase 3: Testing
- [ ] Create test case: identical structure, different parametric weights
- [ ] Create test case: identical structure, identical parametric weights  
- [ ] Create test case: different structures (should still work)
- [ ] Create test case: mixed parametric and numeric
- [ ] Run all existing tests to ensure no regression

### Phase 4: Documentation
- [ ] Add docstring to `_group_by_parametric_signature()`
- [ ] Update `AnnotatedPrepareCostLayer` docstring to mention parametric support
- [ ] Add example in docstring or how-to guide
- [ ] Update CHANGELOG or release notes

## Test Cases

### Test 1: Identical Structure, Different Parametric Weights
```python
# 3 complete graphs with different weights
# H = c_0*H_0 + c_1*H_1 + c_2*H_2
# Expected: All parameters [c_0, c_1, c_2, β[0], γ[0]] preserved
```

### Test 2: Identical Structure, Identical Parametric Weights
```python
# 3 complete graphs with same weights but different parameters
# H = c_0*H_0 + c_1*H_1 + c_2*H_2 (all weights = 1.0)
# Expected: All parameters [c_0, c_1, c_2, β[0], γ[0]] preserved
```

### Test 3: Different Structures
```python
# 3 graphs with different edge sets
# Expected: All parameters preserved (already works)
```

### Test 4: Mixed Parametric and Numeric
```python
# H = c_0*H_0 + 1.5*H_1 + c_2*H_2
# Expected: c_0 and c_2 preserved, numeric coefficient handled correctly
```

### Test 5: Single Objective (Regression)
```python
# H = c_0*H_0 (single graph)
# Expected: c_0 preserved, no regression
```

## Edge Cases to Consider

1. **Empty parametric groups**: Skip creating `Commuting2qBlock` for empty groups
2. **Single-node groups**: `Commuting2qBlock` should handle single node correctly
3. **Complex parameter expressions**: `c_0*c_1*γ`, `sin(c_0)*γ`, etc.
4. **Parameter ordering**: Ensure parameter order is preserved in final circuit
5. **Multiple QAOA layers**: Verify fix works across multiple layers

## Success Criteria

1. ✅ All parameters preserved through transpilation for identical structures
2. ✅ Existing numeric optimization still works
3. ✅ All existing tests pass
4. ✅ New tests cover parametric Hamiltonians
5. ✅ No performance regression
6. ✅ Code is well-documented

## Alternative Approaches (Not Chosen)

### Option 2: Configuration Flag
- Add `preserve_parametric_coefficients=True` flag
- **Pros**: Simple, explicit control
- **Cons**: User must know to set it, doesn't auto-detect parametric case

### Option 3: Smarter Parameter Analysis
- Analyze parameter dependencies to detect truly redundant parameters
- **Pros**: Most sophisticated
- **Cons**: Complex, harder to maintain, potential edge cases

## Next Steps

1. Create minimal reproduction test case
2. Verify bug exists
3. Implement `_group_by_parametric_signature()` helper
4. Modify `AnnotatedPrepareCostLayer.run()`
5. Run tests and iterate

## References

- Bug report: User-provided documentation
- Code location: [`qopt_best_practices/transpilation/annotated_transpilation_passes.py`](../qopt_best_practices/transpilation/annotated_transpilation_passes.py)
- Related tests: [`test/test_annotated_transpilation.py`](../test/test_annotated_transpilation.py)