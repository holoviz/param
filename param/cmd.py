"""
parameterized (with parameters) -> command (with options)
"""

# Just an initial prototype right now to see how much work it might be
# to do this.  Have based on argparse, but presumably could be
# something else. Don't know what I'm doing. Haven't decided how to
# organize the code

import param
import inspect
import argparse


# how to convert incoming string to value for parameter
_p2o = {
    param.String: str,
    param.Number: float,
    param.Boolean: bool,
    # etc?
}


class Command(param.ParameterizedFunction):
    __abstract = True

    # TODO: some name formatters

    @classmethod
    def _cmdname(cls):
        return cls.__name__.lower().replace("_","-")
    
    @classmethod
    def _pname2oname(cls,pname):
        return "--"+pname.replace("_","-")

    @classmethod
    def _ptype2otype(cls,ptype):
        # TODO: quick hack - should respect hierarchy
        return _p2o.get(ptype,str)


def _set_defaults(parser,fn):
    parser.set_defaults(func=lambda args: fn( **{k: getattr(args,k) for k in vars(args) if k!='func'} ))
    

def parser_setup_thing(fn,subparsers):

    fnparser = subparsers.add_parser(fn._cmdname(), help=inspect.getdoc(fn))
    for pname,pobj in fn.params().items():
        if pobj.precedence is not None and pobj.precedence<0: # isn't there fn for this?
            continue
        
        things = dict(
            type=fn._ptype2otype(type(pobj)),
            help=pobj.doc,
            default=pobj.default
        )
        if isinstance(pobj,param.Selector):
            things['choices'] = pobj.get_range()
            things['type'] = type(pobj.default) # decide what to do about this - probably no type
    
        fnparser.add_argument(fn._pname2oname(pname),**things)
    
    _set_defaults(fnparser,fn)
    return fnparser
