import param

class TestParameterMetadata:

    def test_metadata_default(self):
        p = param.Parameter()

        assert p.metadata is None

    def test_metadata_set(self):
        m = dict(a=1)
        p = param.Parameter(metadata=m)

        assert p.metadata is m

    def test_metadata_parameterized(self):
        m = {"a": "b"}

        class P(param.Parameterized):
            s = param.Parameter(metadata=m)

        assert P.param.s.metadata is not m
        assert P.param.s.metadata == m

        p = P()
        assert p.param.s.metadata is not m
        assert p.param.s.metadata is not P.param.s.metadata
        assert p.param.s.metadata == m

    def test_metadata_parameterized_inheritance_not_overridden(self):
        m = {"a": "b"}

        class P(param.Parameterized):
            s = param.Parameter(metadata=m)

        class Q(P): pass

        assert P.param.s.metadata is not m
        assert Q.param.s.metadata == m
        assert Q.param.s.metadata is P.param.s.metadata
        q = Q()
        assert q.param.s.metadata is not m
        assert q.param.s.metadata is not Q.param.s.metadata
        assert q.param.s.metadata is not P.param.s.metadata
        assert q.param.s.metadata == m

        m2 = {"c": "d"}
        P.param.s.metadata = m2
        assert Q.param.s.metadata is m2

    def test_metadata_parameterized_inheritance_overridden(self):
        m = {"a": "b"}
        m2 = {"c": "d"}

        class P(param.Parameterized):
            s = param.Parameter(metadata=m)

        class Q(P):
            s = param.Parameter(metadata=m2)

        assert P.param.s.metadata is not m
        assert P.param.s.metadata == m
        assert Q.param.s.metadata is not m2
        assert Q.param.s.metadata == m2
        q = Q()
        assert q.param.s.metadata is not m2
        assert q.param.s.metadata == m2
        assert q.param.s.metadata is not Q.param.s.metadata
        assert q.param.s.metadata is not P.param.s.metadata
