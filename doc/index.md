# Welcome to Param!

<h1><img src="_static/logo_stacked.png" width="125"></h1>

Are you a Python programmer? If so, you need Param, and check out our <a href="https://youtu.be/KP9bRmzinaY">5-minute intro video</a> to see why!

<div align="right" style="margin-right:10% margin-left:10%;">
    <iframe width="100%" height="400" src="https://www.youtube.com/embed/KP9bRmzinaY" title="Param: Python Parameters" frameborder="0" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    <a href="https://tinyurl.com/parampromo">(Download notebook)</a>
</div>

Param is a library for handling all the user-modifiable parameters, arguments, and attributes that control your code. It provides automatic, robust error-checking while dramatically reducing boilerplate code, letting you focus on what you want your code to do rather than on checking for all the possible ways users could supply inappropriate values to a function or class.

Param lets you program declaratively in Python, stating facts about each of your parameters up front. Once you have done that, Param can handle the rest (type checking, range validation, documentation, serialization, and more!). 

Param-based programs tend to contain much less code than other Python programs, instead just having easily readable and maintainable manifests of Parameters for each object or function.  This way your remaining code can be much simpler and clearer, while users can also easily see how to use it properly. Plus, Param doesn't require any  code outside of the Python standard library, making it simple to add to any project. 

Param is also useful as a way to keep your domain-specific code independent of any GUI or other user-interface code, letting you maintain a single codebase to support both GUI and non-GUI usage, with the GUI maintainable by UI experts and the domain-specific code maintained by domain experts.

To quickly see how Param works and can be used, jump straight into the [Getting Started Guide](getting_started), then check out the full functionality in the [User Guide.](user_guide/index)

```{toctree}
---
hidden: true
---
Introduction <self>
Getting Started <getting_started>
User Guide <user_guide/index>
Comparisons <comparisons>
Roadmap <roadmap>
Releases <releases>
API <reference>
About <about>
```
