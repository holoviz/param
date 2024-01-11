# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

import param


class ImportSuite:

    def timeraw_import_param(self):
        return """
        import param
        """


class ParameterSuite:

    def time_instantiation(self):
        param.Parameter()


class ParameterizedSuite:

    def time_class_bare(self):
        class P(param.Parameterized): pass

    def time_class_with_1_parameter(self):
        class P(param.Parameterized):
            x0 = param.Parameter()

    def time_class_with_10_parameter(self):
        class P(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

    def time_class_with_100_parameter(self):
        class P(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()
            x10 = param.Parameter()
            x11 = param.Parameter()
            x12 = param.Parameter()
            x13 = param.Parameter()
            x14 = param.Parameter()
            x15 = param.Parameter()
            x16 = param.Parameter()
            x17 = param.Parameter()
            x18 = param.Parameter()
            x19 = param.Parameter()
            x20 = param.Parameter()
            x21 = param.Parameter()
            x22 = param.Parameter()
            x23 = param.Parameter()
            x24 = param.Parameter()
            x25 = param.Parameter()
            x26 = param.Parameter()
            x27 = param.Parameter()
            x28 = param.Parameter()
            x29 = param.Parameter()
            x30 = param.Parameter()
            x31 = param.Parameter()
            x32 = param.Parameter()
            x33 = param.Parameter()
            x34 = param.Parameter()
            x35 = param.Parameter()
            x36 = param.Parameter()
            x37 = param.Parameter()
            x38 = param.Parameter()
            x39 = param.Parameter()
            x40 = param.Parameter()
            x41 = param.Parameter()
            x42 = param.Parameter()
            x43 = param.Parameter()
            x44 = param.Parameter()
            x45 = param.Parameter()
            x46 = param.Parameter()
            x47 = param.Parameter()
            x48 = param.Parameter()
            x49 = param.Parameter()
            x50 = param.Parameter()
            x51 = param.Parameter()
            x52 = param.Parameter()
            x53 = param.Parameter()
            x54 = param.Parameter()
            x55 = param.Parameter()
            x56 = param.Parameter()
            x57 = param.Parameter()
            x58 = param.Parameter()
            x59 = param.Parameter()
            x60 = param.Parameter()
            x61 = param.Parameter()
            x62 = param.Parameter()
            x63 = param.Parameter()
            x64 = param.Parameter()
            x65 = param.Parameter()
            x66 = param.Parameter()
            x67 = param.Parameter()
            x68 = param.Parameter()
            x69 = param.Parameter()
            x70 = param.Parameter()
            x71 = param.Parameter()
            x72 = param.Parameter()
            x73 = param.Parameter()
            x74 = param.Parameter()
            x75 = param.Parameter()
            x76 = param.Parameter()
            x77 = param.Parameter()
            x78 = param.Parameter()
            x79 = param.Parameter()
            x80 = param.Parameter()
            x81 = param.Parameter()
            x82 = param.Parameter()
            x83 = param.Parameter()
            x84 = param.Parameter()
            x85 = param.Parameter()
            x86 = param.Parameter()
            x87 = param.Parameter()
            x88 = param.Parameter()
            x89 = param.Parameter()
            x90 = param.Parameter()
            x91 = param.Parameter()
            x92 = param.Parameter()
            x93 = param.Parameter()
            x94 = param.Parameter()
            x95 = param.Parameter()
            x96 = param.Parameter()
            x97 = param.Parameter()
            x98 = param.Parameter()
            x99 = param.Parameter()


class ParameterizedInstantiateSuite:

    def setup(self):
        class P1(param.Parameterized):
            x0 = param.Parameter()

        class P10(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

        class P100(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()
            x10 = param.Parameter()
            x11 = param.Parameter()
            x12 = param.Parameter()
            x13 = param.Parameter()
            x14 = param.Parameter()
            x15 = param.Parameter()
            x16 = param.Parameter()
            x17 = param.Parameter()
            x18 = param.Parameter()
            x19 = param.Parameter()
            x20 = param.Parameter()
            x21 = param.Parameter()
            x22 = param.Parameter()
            x23 = param.Parameter()
            x24 = param.Parameter()
            x25 = param.Parameter()
            x26 = param.Parameter()
            x27 = param.Parameter()
            x28 = param.Parameter()
            x29 = param.Parameter()
            x30 = param.Parameter()
            x31 = param.Parameter()
            x32 = param.Parameter()
            x33 = param.Parameter()
            x34 = param.Parameter()
            x35 = param.Parameter()
            x36 = param.Parameter()
            x37 = param.Parameter()
            x38 = param.Parameter()
            x39 = param.Parameter()
            x40 = param.Parameter()
            x41 = param.Parameter()
            x42 = param.Parameter()
            x43 = param.Parameter()
            x44 = param.Parameter()
            x45 = param.Parameter()
            x46 = param.Parameter()
            x47 = param.Parameter()
            x48 = param.Parameter()
            x49 = param.Parameter()
            x50 = param.Parameter()
            x51 = param.Parameter()
            x52 = param.Parameter()
            x53 = param.Parameter()
            x54 = param.Parameter()
            x55 = param.Parameter()
            x56 = param.Parameter()
            x57 = param.Parameter()
            x58 = param.Parameter()
            x59 = param.Parameter()
            x60 = param.Parameter()
            x61 = param.Parameter()
            x62 = param.Parameter()
            x63 = param.Parameter()
            x64 = param.Parameter()
            x65 = param.Parameter()
            x66 = param.Parameter()
            x67 = param.Parameter()
            x68 = param.Parameter()
            x69 = param.Parameter()
            x70 = param.Parameter()
            x71 = param.Parameter()
            x72 = param.Parameter()
            x73 = param.Parameter()
            x74 = param.Parameter()
            x75 = param.Parameter()
            x76 = param.Parameter()
            x77 = param.Parameter()
            x78 = param.Parameter()
            x79 = param.Parameter()
            x80 = param.Parameter()
            x81 = param.Parameter()
            x82 = param.Parameter()
            x83 = param.Parameter()
            x84 = param.Parameter()
            x85 = param.Parameter()
            x86 = param.Parameter()
            x87 = param.Parameter()
            x88 = param.Parameter()
            x89 = param.Parameter()
            x90 = param.Parameter()
            x91 = param.Parameter()
            x92 = param.Parameter()
            x93 = param.Parameter()
            x94 = param.Parameter()
            x95 = param.Parameter()
            x96 = param.Parameter()
            x97 = param.Parameter()
            x98 = param.Parameter()
            x99 = param.Parameter()

        self.P1 = P1
        self.P10 = P10
        self.P100 = P100

    def time_1_parameters(self):
        self.P1()

    def time_10_parameters(self):
        self.P10()

    def time_100_parameters(self):
        self.P100()


class ParameterizedParamAccessSuite:

    def setup(self):
        class P1(param.Parameterized):
            x0 = param.Parameter()

        self.P1 = P1
        self.p1 = P1()

    def time_class(self):
        self.P1.param

    def time_instance(self):
        self.p1.param

class ParameterizedParamContainsSuite:

    def setup(self):
        class P1(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()

        self.P1 = P1
        self.p1 = P1()

    def time_class(self):
        'x5' in self.P1.param

    def time_instance(self):
        'x5' in self.p1.param


class ParameterizedSetattrSuite:

    def setup(self):
        class P1(param.Parameterized):
            x0 = param.Parameter()

        self.P1 = P1
        self.p1 = P1(x0=0)

    def time_class(self):
        self.P1.x0 = 1

    def time_instance(self):
        self.p1.x0 = 1


class ParameterizedDependsSuite:

    def time_declarative_1_parameter(self):
        class P(param.Parameterized):
            x0 = param.Parameter()

            @param.depends('x0')
            def foo0(self): pass

    def time_watch_1_parameter(self):
        class P(param.Parameterized):
            x0 = param.Parameter()

            @param.depends('x0', watch=True)
            def foo0(self): pass

    def time_declarative_10_parameters_separate_cb(self):
        class P(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0')
            def foo0(self): pass

            @param.depends('x1')
            def foo1(self): pass

            @param.depends('x2')
            def foo2(self): pass

            @param.depends('x3')
            def foo3(self): pass

            @param.depends('x4')
            def foo4(self): pass

            @param.depends('x5')
            def foo5(self): pass

            @param.depends('x6')
            def foo6(self): pass

            @param.depends('x7')
            def foo7(self): pass

            @param.depends('x8')
            def foo8(self): pass

            @param.depends('x9')
            def foo9(self): pass

    def time_declarative_10_parameters_shared_cb(self):
        class P(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9')
            def foo(self): pass

    def time_watch_10_parameters_separate_cb(self):
        class P(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0', watch=True)
            def foo0(self): pass

            @param.depends('x1', watch=True)
            def foo1(self): pass

            @param.depends('x2', watch=True)
            def foo2(self): pass

            @param.depends('x3', watch=True)
            def foo3(self): pass

            @param.depends('x4', watch=True)
            def foo4(self): pass

            @param.depends('x5', watch=True)
            def foo5(self): pass

            @param.depends('x6', watch=True)
            def foo6(self): pass

            @param.depends('x7', watch=True)
            def foo7(self): pass

            @param.depends('x8', watch=True)
            def foo8(self): pass

            @param.depends('x9', watch=True)
            def foo9(self): pass

    def time_watch_10_parameters_shared_cb(self):
        class P(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', watch=True)
            def foo(self): pass


class ParameterizedDependsInstantiateSuite:

    def setup(self):
        class P1Declarative(param.Parameterized):
            x0 = param.Parameter()

            @param.depends('x0')
            def foo0(self): pass

        class P1Watch(param.Parameterized):
            x0 = param.Parameter()

            @param.depends('x0', watch=True)
            def foo0(self): pass

        class P10DeclarativeSeparate(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0')
            def foo0(self): pass

            @param.depends('x1')
            def foo1(self): pass

            @param.depends('x2')
            def foo2(self): pass

            @param.depends('x3')
            def foo3(self): pass

            @param.depends('x4')
            def foo4(self): pass

            @param.depends('x5')
            def foo5(self): pass

            @param.depends('x6')
            def foo6(self): pass

            @param.depends('x7')
            def foo7(self): pass

            @param.depends('x8')
            def foo8(self): pass

            @param.depends('x9')
            def foo9(self): pass

        class P10DeclarativeShared(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9')
            def foo(self): pass

        class P10WatchSeparate(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0', watch=True)
            def foo0(self): pass

            @param.depends('x1', watch=True)
            def foo1(self): pass

            @param.depends('x2', watch=True)
            def foo2(self): pass

            @param.depends('x3', watch=True)
            def foo3(self): pass

            @param.depends('x4', watch=True)
            def foo4(self): pass

            @param.depends('x5', watch=True)
            def foo5(self): pass

            @param.depends('x6', watch=True)
            def foo6(self): pass

            @param.depends('x7', watch=True)
            def foo7(self): pass

            @param.depends('x8', watch=True)
            def foo8(self): pass

            @param.depends('x9', watch=True)
            def foo9(self): pass


        class P10WatchShared(param.Parameterized):
            x0 = param.Parameter()
            x1 = param.Parameter()
            x2 = param.Parameter()
            x3 = param.Parameter()
            x4 = param.Parameter()
            x5 = param.Parameter()
            x6 = param.Parameter()
            x7 = param.Parameter()
            x8 = param.Parameter()
            x9 = param.Parameter()

            @param.depends('x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', watch=True)
            def foo(self): pass


        self.P1Declarative = P1Declarative
        self.P1Watch = P1Watch
        self.P10DeclarativeSeparate = P10DeclarativeSeparate
        self.P10DeclarativeShared = P10DeclarativeShared
        self.P10WatchSeparate = P10WatchSeparate
        self.P10WatchShared = P10WatchShared

    def time_declarative_1_parameter(self):
        self.P1Declarative()

    def time_watch_1_parameter(self):
        self.P1Watch()

    def time_declarative_10_parameters_separate_cb(self):
        self.P10DeclarativeSeparate()

    def time_declarative_10_parameters_shared_cb(self):
        self.P10DeclarativeShared()

    def time_watch_10_parameters_separate_cb(self):
        self.P10WatchSeparate()

    def time_watch_10_parameters_shared_cb(self):
        self.P10WatchShared()


class WatcherSuite:

    def setup(self):
        class P(param.Parameterized):
            x0 = param.Parameter(0)

            @param.depends('x0', watch=True)
            def foo0(self): pass

        self.p = P()

    def time_trigger(self):
        self.p.x0 += 1
