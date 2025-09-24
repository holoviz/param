# Param - Static Typing - Analysis

This document fixes the problem described in [problem.md](problem.md).

## Updated Findings (2025)

### Param Descriptors and Typing
- Param descriptors (e.g., param.String, param.Number) can provide good attribute type inference in mypy if their stubs define correct __get__ return types (e.g., str, Optional[str], float).
- Type annotations on descriptor assignments cause mypy errors unless suppressed with # type: ignore[assignment].
- Wrapper functions using @overload (e.g., param_string) can help mypy infer the type of the value returned by the function, but the attribute is still a descriptor, so __init__ signatures are not synthesized.
- Mypy does not automatically add Param attributes to the __init__ signature, even with @dataclass_transform or wrapper functions. Only dataclasses, attrs, and pydantic are special-cased for this behavior.
- For best results, use stubs for descriptors and, if needed, class-specific stubs for correct __init__ signatures.

### Wrapper Functions with @overload
- Providing wrapper functions like param_string with @overload can improve type inference for value-based APIs.
- For descriptor-based APIs like Param, wrapper functions do not solve the main static typing challenge: mypy cannot synthesize the correct __init__ signature or fully understand dynamic descriptor behavior.
- Therefore, wrapper functions are not recommended as a general solution for Param static typing. They may be useful for value-oriented usage, but not for descriptor-based classes.

## Potential Solutions

### 1. PEP 681 – Data Class Transforms
PEP 681’s @dataclass_transform helps type checkers recognize dataclass-like behavior, but does not synthesize __init__ signatures for Param-based classes automatically. Stubs or code generation are still needed for full support.

### 2. Custom Type Checker Plugins
Custom plugins can provide better support but require ongoing maintenance and are less future-proof.

### 3. Type Annotations via Code Generation or Metaclass Magic
Dynamic type hint generation is possible but complex and hard to maintain.

### 4. Integration with Dataclasses or Pydantic
Conversion utilities can help users who need full static typing.

### 5. Documentation and IDE Integration
Improved documentation and stubs help users get better type support.

---

## Recommendations
- Adopt PEP 681’s @dataclass_transform for Param’s metaclass or base class.
- Provide and maintain high-quality stubs for Param descriptors.
- Use class-specific stubs for full static typing, including __init__ signatures.
- Consider conversion utilities to dataclasses or Pydantic for users needing strict typing.
- Avoid custom plugins unless absolutely necessary.
- Do not recommend wrapper functions with @overload as a general solution for Param static typing.