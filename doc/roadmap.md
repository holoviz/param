# Roadmap

Param is a mature library (originally from 2003) that changes very slowly and very rarely; it is fully ready for use in production applications. Major changes are undertaken only after significant discussions and with attention to how existing Param-based applications will be affected. Thus Param users should not expect only slow progress on these roadmap items, but they are listed here in the hopes that they will be useful.

Currently scheduled plans:

- Make there be documentation. We have funding for this and work is already underway. This includes both user guide/tutorial material and reference material, covering both how it's currently used in HoloViz and on the underlying design and general functionality independent of HoloViz (as indeed it predates all of HoloViz). This will be a major step forward in how suitable Param is for general usage.

- Improve the Param website (same time as docs; just make it look decent!)

- Clean up the Parameterized namespace (remove nearly all methods not on .param) and other API warts, scheduled for Param 2.0 since those are breaking changes. See https://github.com/holoviz/param/issues/154 and https://github.com/holoviz/param/issues/233.

- More powerful serialization (to JSON, YAML, and URLs) to make it simpler to persist the state of a Parameterized object. Some support already merged as https://github.com/holoviz/param/pull/414 , but still to be further developed as support for using Parameterized objects to build REST APIS (see https://github.com/holoviz/lumen for example usage).

Other items that are not yet scheduled but would be great to have:

- Integrate more fully with Python 3 language features like [type annotations](https://www.python.org/dev/peps/pep-0526) and/or [data classes], e.g. to respect and validate against declared types without requiring an explicit `param.Parameter` declaration, and to better support IDE type-checking features.

- Integrate and interoperate more fully with other frameworks like Django models, Traitlets, attrs, Django models, or swagger/OpenAPI, each of which capture or can use similar information about parameter names, values, and constraints and so in many cases can easily be converted from one to the other.

- Improve support for Param in editors, automatic formatting tools, linters, document generators, and other tools that process Python code and could be made to have special-purpose optimizations specifically for Parameterized objects.

- Follow PEP8 more strictly: PEP8 definitely wasn't written with Parameters in mind, and it typically results in badly formatted files when applied to Parameterized code. But PEP8 could be applied to Param's own code.

- Triaging open issues: The Param developer team consists of volunteers typically using Param on their projects but not explicity tasked with or funded to work on Param itself. It would thus be great if the more experienced Param users could help address some of the issues that have been raised but not yet solved.

- Improve test coverage

Other [issues](https://github.com/holoviz/param/issues) are collected on Github and will be addressed on various time scales as indicated by the issue's milestone (typically next minor release, next major release, or "wishlist" (not scheduled or assigned to any person but agreed to be desirable). Any contributor is encouraged to attempt to implement a "wishlist" item, though if it is particularly complex or time consuming it is useful to discuss it first with one of the core maintainers (e.g. by stating your intentions on the issue).
