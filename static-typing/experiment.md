# Param - Static Typing - Experiment Results

## experiment.py Summary

The experiment demonstrates how mypy infers types for Param-based classes and wrapper function-based APIs:

- Param descriptors (e.g., param.String, param.Number) with good stubs allow mypy to infer correct types for instance attributes (e.g., str, Optional[str], float).
- Wrapper functions using @overload (e.g., param_string) can help mypy infer the type of the value returned by the function, but the attribute is still a descriptor, so __init__ signatures are not synthesized.
- Type annotations on descriptor assignments cause mypy errors unless suppressed with # type: ignore[assignment].
- Mypy does not automatically add Param attributes to the __init__ signature, even with @dataclass_transform or wrapper functions. Only dataclasses, attrs, and pydantic are special-cased for this behavior.
- For best results, use stubs for descriptors and, if needed, class-specific stubs for correct __init__ signatures.

## Key Findings
- Param descriptors can provide good attribute type inference with stubs.
- Wrapper functions with @overload help with value type inference, but not with __init__ signatures.
- Mypy does not synthesize __init__ signatures for Param-based classes automatically.
- Class-specific stubs are required for full static typing support, including constructor signatures.
