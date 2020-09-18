In 2018, we moved most of `Parameterized` onto a `param` namespace
object, expecting this to be the public API of param 2.0, and cleaning
up the namespace of user classes.

The new API has been in use for a while within holoviz projects, but
we're still changing it. Meanwhile, the previous API remains
available.

The original API's tests were copied into an `API0` subdirectory,
while tests in `API1` use the new API.

(Probably not ideal to just copy everything, and cleaning up would be
great, but this explains the two directories you see here.)
