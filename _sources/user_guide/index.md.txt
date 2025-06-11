# User Guide

This user guide provides detailed information about how to use Param, assuming you have worked through the Getting Started guide.

- [Simplifying Codebases](./Simplifying_Codebases): How Param allows you to eliminate boilerplate and unsafe code
- [Parameters](./Parameters): Using parameters (Class vs. instance parameters, setting defaults, etc.)
- [Parameter Types](./Parameter_Types): Predefined Parameter classes available for your use
- [Dependencies and Watchers](./Dependencies_and_Watchers): Expressing relationships between parameters and parameters or code, and triggering events.
- [References](./References): Allowing parameters to resolve references to other parameters, reactive expressions, functions and generators.
- [Reactive Expressions](./Reactive_Expressions): How to write expressions and functions that automatically re-evaluate when their parameter inputs change.
- [Generators](./Generators): Using (asynchronous) generators to drive events on parameters and expressions in a "push" based model.
- [Serialization and Persistence](./Serialization_and_Persistence): Saving the state of a Parameterized object to a text, script, or pickle file
- [Outputs](./Outputs): Output types and connecting output to Parameter inputs
- [Logging and Warnings](./Logging_and_Warnings): Logging, messaging, warning, and raising errors on Parameterized objects
- [ParameterizedFunctions](./ParameterizedFunctions): Parameterized function objects, for configurable callables
- [Dynamic Parameters](./Dynamic_Parameters): Using dynamic parameter values with and without Numbergen
- [How Param Works](./How_Param_Works): Internal details, for Param developers and power users
- [Using Param in GUIs](https://panel.holoviz.org/how_to/param/index.html): (external site) Using Param with Panel to make GUIs

```{toctree}
---
hidden: true
maxdepth: 2
---
Overview <self>
Simplifying Codebases <Simplifying_Codebases>
Parameters <Parameters>
Parameter Types <Parameter_Types>
Dependencies and Watchers <Dependencies_and_Watchers>
References <References>
Reactive Expressions <Reactive_Expressions>
Generators <Generators>
Serialization and Persistence <Serialization_and_Persistence>
Outputs <Outputs>
Logging and Warnings <Logging_and_Warnings>
ParameterizedFunctions <ParameterizedFunctions>
Dynamic Parameters <Dynamic_Parameters>
How Param Works <How_Param_Works>
```
