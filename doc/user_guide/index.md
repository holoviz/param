# User Guide

This user guide provides detailed information about how to use Param, assuming you have worked through the Getting Started guide. Sections marked TODO are still in development as of 7/2021.

- [Simplifying Codebases](./Simplifying_Codebases): How Param allows you to eliminate boilerplate and unsafe code 
- [Parameters](./Parameters): Using parameters (Class vs. instance parameters, setting defaults, etc.)
- [Parameter Types](./Parameter_Types): Predefined Parameter classes available for your use
- Dependencies and Watchers: Expressing relationships between parameters and parameters or code, and triggering events (TODO)
- Serialization and Persistence: Saving the state of a Parameterized object to a text, script, or pickle file (TODO)
- Customization: Extending Param with custom Parameter types (TODO)
- Outputs: Output types and connecting output to Parameter inputs (TODO)
- [Logging and Messages](./Logging_and_Messages): Logging, messaging, warning, and raising errors on Parameterized objects
- [ParameterizedFunctions](./ParameterizedFunctions): Parameterized function objects, for configurable callables
- Dynamic Parameters: Using dynamic parameter values with and without Numbergen (TODO)
- [How Param works](How_Param_Works): Internal details, for Param developers and power users

```{toctree}
---
hidden: true
:maxdepth: 2
---
Overview <index>
Simplifying Codebases <Simplifying_Codebases>
Parameters <Parameters>
Parameter Types <Parameter_Types>
Logging and Messages <Logging_and_Messages>
ParameterizedFunctions <ParameterizedFunctions>
How Param Works <How_Param_Works>
```
