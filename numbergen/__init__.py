"""
Callable objects that generate numbers according to different distributions.
"""

import random
import operator
import hashlib
import struct
import fractions

from math import e,pi

import param


from param.version import Version
__version__ = Version(release=(1,2,1), fpath=__file__,
                      commit="$Format:%h$", reponame="param")


class TimeAware(param.Parameterized):
    """
    Class of objects that have access to a global time function
    and have the option of using it to generate time-dependent values
    as necessary.

    In the simplest case, an object could act as a strict function of
    time, returning the current time transformed according to a fixed
    equation.  Other objects may support locking their results to a
    timebase, but also work without time.  For instance, objects with
    random state could return a new random value for every call, with
    no notion of time, or could always return the same value until the
    global time changes.  Subclasses should thus provide an ability to
    return a time-dependent value, but may not always do so.
    """

    time_dependent = param.Boolean(default=False,  doc="""
       Whether the given time_fn should be used to constrain the
       results generated.""")

    time_fn = param.Callable(default=param.Dynamic.time_fn, doc="""
        Callable used to specify the time that determines the state
        and return value of the object, if time_dependent=True.""")


    def __init__(self, **params):
        super(TimeAware, self).__init__(**params)
        self._check_time_fn()


    def _check_time_fn(self, time_instance=False):
        """
        If time_fn is the global time function supplied by
        param.Dynamic.time_fn, make sure Dynamic parameters are using
        this time function to control their behaviour.

        If time_instance is True, time_fn must be a param.Time instance.
        """
        if time_instance and not isinstance(self.time_fn, param.Time):
            raise AssertionError("%s requires a Time object"
                                 % self.__class__.__name__)

        if self.time_dependent:
            global_timefn = self.time_fn is param.Dynamic.time_fn
            if global_timefn and not param.Dynamic.time_dependent:
                raise AssertionError("Cannot use Dynamic.time_fn as"
                                     " parameters are ignoring time.")


class TimeDependent(TimeAware):
    """
    Objects that have access to a time function that determines the
    output value. As a function of time, this type of object should
    allow time values to be randomly jumped forwards or backwards,
    but for a given time point, the results should remain constant.

    The time_fn must be an instance of param.Time, to ensure all the
    facilities necessary for safely navigating the timeline are
    available.
    """

    time_dependent = param.Boolean(default=True, readonly=True, doc="""
       Read-only parameter that is always True.""")

    def _check_time_fn(self):
        super(TimeDependent,self)._check_time_fn(time_instance=True)



class NumberGenerator(param.Parameterized):
    """
    Abstract base class for any object that when called produces a number.

    Primarily provides support for using NumberGenerators in simple
    arithmetic expressions, such as abs((x+y)/z), where x,y,z are
    NumberGenerators or numbers.
    """

    def __call__(self):
        raise NotImplementedError

    # Could define any of Python's operators here, esp. if they have operator or ufunc equivalents
    def __add__      (self,operand): return BinaryOperator(self,operand,operator.add)
    def __sub__      (self,operand): return BinaryOperator(self,operand,operator.sub)
    def __mul__      (self,operand): return BinaryOperator(self,operand,operator.mul)
    def __mod__      (self,operand): return BinaryOperator(self,operand,operator.mod)
    def __pow__      (self,operand): return BinaryOperator(self,operand,operator.pow)
    def __div__      (self,operand): return BinaryOperator(self,operand,operator.div)
    def __truediv__  (self,operand): return BinaryOperator(self,operand,operator.truediv)
    def __floordiv__ (self,operand): return BinaryOperator(self,operand,operator.floordiv)

    def __radd__     (self,operand): return BinaryOperator(self,operand,operator.add,True)
    def __rsub__     (self,operand): return BinaryOperator(self,operand,operator.sub,True)
    def __rmul__     (self,operand): return BinaryOperator(self,operand,operator.mul,True)
    def __rmod__     (self,operand): return BinaryOperator(self,operand,operator.mod,True)
    def __rpow__     (self,operand): return BinaryOperator(self,operand,operator.pow,True)
    def __rdiv__     (self,operand): return BinaryOperator(self,operand,operator.div,True)
    def __rtruediv__ (self,operand): return BinaryOperator(self,operand,operator.truediv,True)
    def __rfloordiv__(self,operand): return BinaryOperator(self,operand,operator.floordiv,True)

    def __neg__ (self): return UnaryOperator(self,operator.neg)
    def __pos__ (self): return UnaryOperator(self,operator.pos)
    def __abs__ (self): return UnaryOperator(self,operator.abs)



class BinaryOperator(NumberGenerator):
    """Applies any binary operator to NumberGenerators or numbers to yield a NumberGenerator."""

    def __init__(self,lhs,rhs,operator,reverse=False,**args):
        """
        Accepts two NumberGenerator operands, an operator, and
        optional arguments to be provided to the operator when calling
        it on the two operands.
        """
        # Note that it's currently not possible to set
        # parameters in the superclass when creating an instance,
        # because **args is used by this class itself.
        super(BinaryOperator,self).__init__()

        if reverse:
            self.lhs=rhs
            self.rhs=lhs
        else:
            self.lhs=lhs
            self.rhs=rhs
        self.operator=operator
        self.args=args

    def __call__(self):
        return self.operator(self.lhs() if callable(self.lhs) else self.lhs,
                             self.rhs() if callable(self.rhs) else self.rhs, **self.args)



class UnaryOperator(NumberGenerator):
    """Applies any unary operator to a NumberGenerator to yield another NumberGenerator."""

    def __init__(self,operand,operator,**args):
        """
        Accepts a NumberGenerator operand, an operator, and
        optional arguments to be provided to the operator when calling
        it on the operand.
        """
        # Note that it's currently not possible to set
        # parameters in the superclass when creating an instance,
        # because **args is used by this class itself.
        super(UnaryOperator,self).__init__()

        self.operand=operand
        self.operator=operator
        self.args=args

    def __call__(self):
        return self.operator(self.operand(),**self.args)



class Hash(object):
    """
    A platform- and architecture-independent hash function 
    (unlike Python's inbuilt hash()) for use with an ordered
    collection of rationals or integers.

    The supplied name sets the initial hash state.  The output from
    each call is a 64-bit integer. The number of inputs (integer or
    rational numbers) to be supplied for __call__ must be specified in
    the constructor and must stay constant across calls.
    """
    def __init__(self, name, input_count):
        self.name = name
        self._digest = hashlib.md5()
        self._digest.update(name.encode())
        struct_format = "!"+" ".join(["I"] * (input_count * 2))
        self._hash_struct = struct.Struct(struct_format)


    def _rational(self, val):
        """Convert the given value to a rational, if necessary."""
        if isinstance(val, int):
            denom , numer = 1, val
        elif hasattr(val, 'numer'):
            (numer, denom) = (int(val.numer()), int(val.denom()))
        else:
            self.warning("Casting type '%s' to Fraction.fraction"
                         % type(val).__name__)
            frac = fractions.Fraction(str(val))
            denom, numer = frac.denominator, frac.numerator
        return denom, numer


    def __getstate__(self):
        """
        Avoid Hashlib.md5 TypeError in deepcopy (hashlib issue)
        """
        d = self.__dict__.copy()
        d.pop('_digest')
        return d


    def __setstate__(self, d):
        self._digest = hashlib.md5()
        self._digest.update(d['name'].encode())
        self.__dict__.update(d)


    def __call__(self, *vals):
        """
        Given integer or rational inputs, generate a cross-platform,
        architecture-independent integer hash.
        """
        # Convert inputs to (denom, numer) pairs with integers
        # becoming (int, 1) pairs to match gmpy.mpqs for int values.
        pairs = [self._rational(val) for val in vals]
        # Unpack pairs and fill struct with ints to update md5 hash
        ints = [el for pair in pairs for el in pair]
        digest = self._digest.copy()
        digest.update(self._hash_struct.pack(*ints))
        # Convert from hex string to 64 bit int
        return int(digest.hexdigest()[:15], 16)



class RandomDistribution(NumberGenerator, TimeAware):
    """
    Python's random module provides the Random class, which can be
    instantiated to give an object that can be asked to generate
    numbers from any of several different random distributions
    (e.g. uniform, Gaussian).

    To make it easier to use these, Numbergen provides here a
    hierarchy of classes, each tied to a particular random
    distribution. RandomDistributions support setting parameters on
    creation rather than passing them each call, and allow pickling to
    work properly.  Code that uses these classes will be independent
    of how many parameters are used by the underlying distribution,
    and can simply treat them as a generic source of random numbers.

    The underlying random.Random() instance and all its methods can be
    accessed from the 'random_generator' attribute.

    RandomDistributions are TimeAware, and thus can be locked to
    a global time if desired.  By default, time_dependent=False, and
    so a new random value will be generated each time these objects
    are called.  If you have a global time function, you can set
    time_dependent=True, so that the random values will instead be
    constant at any given time, changing only when the time changes.
    Using time_dependent values can help you obtain fully reproducible
    streams of random numbers, even if you e.g. move time forwards and
    backwards for testing.

    If declared time_dependent, a hash is generated for seeding the
    random state on each call, using a triple consisting of the object
    name, the time returned by time_fn and the global value of
    param.random_seed. As a consequence, for a given name and fixed
    value of param.random_seed, the random values generated will be a
    fixed function of time.

    If the object name has not been set and time_dependent is True, a
    message is generated warning that the default object name is
    dependent on the order of instantiation.  To ensure that the
    random number stream will remain constant even if other objects
    are added or reordered in your file, supply a unique name
    explicitly when you construct the RandomDistribution object.
    """

    __abstract = True


    def __init__(self,**params):
        """
        Initialize a new Random() instance and store the supplied
        positional and keyword arguments.

        If seed=X is specified, sets the Random() instance's seed.
        Otherwise, calls the instance's jumpahead() method to get a
        state very likely to be different from any just used.
        """
        self.random_generator = random.Random()

        seed = params.pop('seed', None)
        super(RandomDistribution,self).__init__(**params)

        if seed is not None:
            self.random_generator.seed(seed)
        else:
            self.random_generator.jumpahead(10)

        self._hashfn = Hash(self.name, input_count=2)
        self._verify_constrained_hash()
        if self.time_dependent:
            self._hash_and_seed()


    def _verify_constrained_hash(self):
        changed_params = dict(self.get_param_values(onlychanged=True))
        if self.time_dependent and ('name' not in changed_params):
            self.warning("Default object name used to set the seed: "
                         "random values conditional on object instantiation order.")

    def _hash_and_seed(self):
        # Assumes param.random_seed is an integer or rational type
        hashval = self._hashfn(self.time_fn(), param.random_seed)
        self.random_generator.seed(hashval)


    def __call__(self):
        if self.time_dependent:
            self._hash_and_seed()



class UniformRandom(RandomDistribution):
    """
    Specified with lbound and ubound; when called, return a random
    number in the range [lbound, ubound).

    See the random module for further details.
    """

    lbound = param.Number(default=0.0,doc="inclusive lower bound")

    ubound = param.Number(default=1.0,doc="exclusive upper bound")


    def __call__(self):
        super(UniformRandom, self).__call__()
        return self.random_generator.uniform(self.lbound,self.ubound)



class UniformRandomOffset(RandomDistribution):
    """
    Identical to UniformRandom, but specified by mean and range.
    When called, return a random number in the range
    [mean - range/2, mean + range/2).

    See the random module for further details.
    """

    mean = param.Number(default=0.0, doc="""Mean value""")

    range = param.Number(default=1.0, bounds=(0.0,None), doc="""
        Difference of maximum and minimum value""")


    def __call__(self):
        super(UniformRandomOffset, self).__call__()
        return self.random_generator.uniform(
                self.mean - self.range / 2.0,
                self.mean + self.range / 2.0)



class UniformRandomInt(RandomDistribution):
    """
    Specified with lbound and ubound; when called, return a random
    number in the inclusive range [lbound, ubound].

    See the randint function in the random module for further details.
    """

    lbound = param.Number(default=0,doc="inclusive lower bound")
    ubound = param.Number(default=1000,doc="inclusive upper bound")


    def __call__(self):
        super(UniformRandomInt, self).__call__()
        x = self.random_generator.randint(self.lbound,self.ubound)
        return x



class Choice(RandomDistribution):
    """
    Return a random element from the specified list of choices.

    Accepts items of any type, though they are typically numbers.
    See the choice() function in the random module for further details.
    """

    choices = param.List(default=[0,1],
        doc="List of items from which to select.")


    def __call__(self):
        super(Choice, self).__call__()
        return self.random_generator.choice(self.choices)



class NormalRandom(RandomDistribution):
    """
    Normally distributed (Gaussian) random number.

    Specified with mean mu and standard deviation sigma.
    See the random module for further details.
    """

    mu = param.Number(default=0.0,doc="Mean value.")

    sigma = param.Number(default=1.0,bounds=(0.0,None),doc="Standard deviation.")


    def __call__(self):
        super(NormalRandom, self).__call__()
        return self.random_generator.normalvariate(self.mu,self.sigma)



class VonMisesRandom(RandomDistribution):
    """
    Circularly normal distributed random number.

    If kappa is zero, this distribution reduces to a uniform random
    angle over the range 0 to 2*pi.  Otherwise, it is concentrated to
    a greater or lesser degree (determined by kappa) around the mean
    mu.  For large kappa (narrow peaks), this distribution approaches
    the Gaussian (normal) distribution with variance 1/kappa.  See the
    random module for further details.
    """

    mu = param.Number(default=0.0,softbounds=(0.0,2*pi),doc="""
        Mean value, typically in the range 0 to 2*pi.""")

    kappa = param.Number(default=1.0,bounds=(0.0,None),softbounds=(0.0,50.0),doc="""
        Concentration (inverse variance).""")


    def __call__(self):
        super(VonMisesRandom, self).__call__()
        return self.random_generator.vonmisesvariate(self.mu,self.kappa)




class ScaledTime(NumberGenerator, TimeDependent):
    """
    The current time multiplied by some conversion factor.
    """

    factor = param.Number(default=1.0, doc="""
       The factor to be multiplied by the current time value.""")


    def __call__(self):
        return float(self.time_fn() * self.factor)



class BoxCar(NumberGenerator, TimeDependent):
    """
    The boxcar function over the specified time interval. The bounds
    are exclusive: zero is returned at the onset time and at the
    offset (onset+duration).

    If duration is None, then this reduces to a step function around the
    onset value with no offset.

    See http://en.wikipedia.org/wiki/Boxcar_function
    """

    onset = param.Number(0.0, doc="Time of onset.")

    duration = param.Number(None, allow_None=True, bounds=(0.0,None), doc="""
        Duration of step value.""")


    def __call__(self):
        if self.time_fn() <= self.onset:
            return 0.0
        elif (self.duration is not None) and (self.time_fn() > self.onset + self.duration):
            return 0.0
        else:
            return 1.0



class SquareWave(NumberGenerator, TimeDependent):
    """
    Generate a square wave with 'on' periods returning 1.0 and
    'off'periods returning 0.0 of specified duration(s). By default
    the portion of time spent in the high state matches the time spent
    in the low state (a duty cycle of 50%), but the duty cycle can be
    controlled if desired.

    The 'on' state begins after a time specified by the 'onset'
    parameter.  The onset duration supplied must be less than the off
    duration.
    """

    onset = param.Number(0.0, doc="""Time of onset of the first 'on'
        state relative to time 0. Must be set to a value less than the
        'off_duration' parameter.""")

    duration = param.Number(1.0, allow_None=False, bounds=(0.0,None), doc="""
         Duration of the 'on' state during which a value of 1.0 is
         returned.""")

    off_duration = param.Number(default=None, allow_None=True,
                                bounds=(0.0,None), doc="""
        Duration of the 'off' value state during which a value of 0.0
        is returned. By default, this duration matches the value of
        the 'duration' parameter.""")


    def __init__(self, **params):
        super(SquareWave,self).__init__(**params)

        if self.off_duration is None:
            self.off_duration = self.duration

        if self.onset > self.off_duration:
            raise AssertionError("Onset value needs to be less than %s" % self.onset)


    def __call__(self):
        phase_offset = (self.time_fn() - self.onset) % (self.duration + self.off_duration)
        if phase_offset < self.duration:
            return 1.0
        else:
            return 0.0



class ExponentialDecay(NumberGenerator, TimeDependent):
    """
    Function object that provides a value that decays according to an
    exponential function, based on a given time function.

    Returns starting_value*base^(-time/time_constant).

    See http://en.wikipedia.org/wiki/Exponential_decay.
    """

    starting_value = param.Number(1.0, doc="Value used for time zero.")

    ending_value = param.Number(0.0, doc="Value used for time infinity.")

    time_constant = param.Number(10000,doc="""
        Time scale for the exponential; large values give slow decay.""")

    base = param.Number(e, doc="""
        Base of the exponent; the default yields starting_value*exp(-t/time_constant).
        Another popular choice of base is 2, which allows the
        time_constant to be interpreted as a half-life.""")


    def __call__(self):
        Vi = self.starting_value
        Vm = self.ending_value
        return Vm + (Vi - Vm) * self.base**(-1.0*float(self.time_fn())/
                                                 float(self.time_constant))



class TimeSampledFn(NumberGenerator, TimeDependent):
    """
    Samples the values supplied by a time_dependent callable at
    regular intervals of duration 'period', with the sampled value
    held constant within each interval.
    """

    period = param.Number(default=1.0, bounds=(0.0,None),
        inclusive_bounds=(False,True), softbounds=(0.0,5.0), doc="""
        The periodicity with which the values of fn are sampled.""")

    offset = param.Number(default=0.0, bounds=(0.0,None),
                          softbounds=(0.0,5.0), doc="""
        The offset from time 0.0 at which the first sample will be drawn.
        Must be less than the value of period.""")

    fn = param.Callable(doc="""
        The time-dependent function used to generate the sampled values.""")


    def __init__(self, **params):
        super(TimeSampledFn, self).__init__(**params)

        if not getattr(self.fn,'time_dependent', False):
            raise Exception("The function 'fn' needs to be time dependent.")

        if self.time_fn != self.fn.time_fn:
            raise Exception("Objects do not share the same time_fn")

        if self.offset >= self.period:
            raise Exception("The onset value must be less than the period.")


    def __call__(self):
        current_time = self.time_fn()
        current_time += self.offset
        difference = current_time % self.period
        with self.time_fn as t:
            t(current_time - difference - self.offset)
            value = self.fn()
        return value



class BoundedNumber(NumberGenerator):
    """
    Function object that silently enforces numeric bounds on values
    returned by a callable object.
    """

    generator = param.Callable(None, doc="Object to call to generate values.")

    bounds = param.Parameter((None,None), doc="""
        Legal range for the value returned, as a pair.

        The default bounds are (None,None), meaning there are actually
        no bounds.  One or both bounds can be set by specifying a
        value.  For instance, bounds=(None,10) means there is no lower
        bound, and an upper bound of 10.""")


    def __call__(self):
        val = self.generator()
        min_, max_ = self.bounds
        if   min_ != None and val < min_: return min_
        elif max_ != None and val > max_: return max_
        else: return val


_public = list(set([_k for _k,_v in locals().items() if isinstance(_v,type) and issubclass(_v,NumberGenerator)]))
__all__ = _public
