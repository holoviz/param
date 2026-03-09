# Welcome to Param!

<h1><img src="_static/logo_stacked.png" width="125"></h1>

**Param** is a zero-dependency Python library that provides two main features:

- Easily create classes with **rich, declarative attributes** - `Parameter` objects - that include extended metadata for various purposes such as runtime type and range validation, documentation strings, default values or factories, nullability, etc. In this sense, Param is conceptually similar to libraries like Pydantic, Python's dataclasses, or Traitlets.
- A suite of expressive and composable APIs for **reactive programming**, enabling automatic updates on attribute changes, and declaring complex reactive dependencies and expressions that can be introspected by other frameworks to implement their own reactive workflows.

This combination of **rich attributes** and **reactive APIs** makes Param a solid foundation for constructing user interfaces, graphical applications, and responsive systems where data integrity and automatic synchronization are paramount. In fact, Param serves as the backbone of HoloViz’s [Panel](https://panel.holoviz.org) and [HoloViews](https://holoviews.org) libraries, powering their rich interactivity and data-driven workflows.

Here is a very simple example showing both features at play. We declare a UserForm class with three parameters: `age` as an *Integer* parameter and and `name` as a *String* parameter for user data, and `submit` as an *Event* parameter to simulate a button in a user interface. We also declare that the `save_user_to_db` method should be called automatically when the value of the `submit` attribute changes.

```python
import param

class UserForm(param.Parameterized):
    age = param.Integer(bounds=(0, None), doc='User age')
    name = param.String(doc='User name')
    submit = param.Event()

    @param.depends('submit', watch=True)
    def save_user_to_db(self):
        print(f'Saving user to db: name={self.name}, age={self.age}')
        ...

user = UserForm(name='Bob', age=25)

user.submit = True  # => Saving user to db: name=Bob, age=25
```

To quickly see how Param works and can be used, jump straight into the [Getting Started Guide](getting_started), then check out the full functionality in the [User Guide.](user_guide/index)

```{toctree}
---
hidden: true
---
Getting Started <getting_started>
User Guide <user_guide/index>
API <reference/index>
Releases <releases>
Upgrade Guide <upgrade_guide>
Comparisons <comparisons>
Roadmap <roadmap>
Developer Guide <developer_guide>
About <about>
```
