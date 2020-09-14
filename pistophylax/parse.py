from typing import TYPE_CHECKING
from lark import Lark, Transformer as BaseTransformer, v_args
from lark.exceptions import VisitError
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources
from .logic import Sequent, Box, WFF, Connective, Atom, Falsum
from . import error
if TYPE_CHECKING:
    from .context import Session


def init_parser(debug=False):
    grammar = pkg_resources.read_text(__package__, 'grammar.lark')
    return Lark(grammar, parser='lalr', debug=debug, propagate_positions=True, maybe_placeholders=True)

def _errorswithcontext(func):
    def wrap(self, args, meta):
        try:
            return func(self, args, meta)
        except error.LogicError as e:
            raise error.ContextualLogicError(e, self.session.file, meta.line, meta.column)
        except VisitError as e:
            if isinstance(e.orig_exc, error.ContextualLogicError):
                raise e.orig_exc
            #elif isinstance(e.orig_exc, error.LogicError):
            #    raise error.ContextualLogicError(e.orig_exc, self.session.file, meta.line, meta.column)
            else:
                raise
    return wrap

class Transformer(BaseTransformer):
    def __init__(self, session: 'Session'):
        self.session = session
        super().__init__()

    start = lambda self, stmts: stmts

    @v_args(meta=True)
    @_errorswithcontext
    def include(self, args, meta):
        return self.session.load(args[0][1:-1])

    @v_args(meta=True)
    @_errorswithcontext
    def proof(self, args, meta):
        name, (premises, conclusion), *statements = args
        # pop context
        if not self.session.ctx().is_top():
            raise error.ProofError('unclosed boxes at proof end')
        lines, premisecount = self.session.ctx().pop()
        lines = list(lines.values())
        # check correct premises discharged
        if premisecount != len(premises):
            raise error.ProofError(f'incorrect number of premises used in proof: got {premisecount}, expected {len(premises)}')
        for i in range(0, premisecount):
            if lines[i] != premises[i]:
                raise error.ProofError(f'premise #{i+1} {lines[i]} does not match expected {premises[i]}')
        # check last line is correct conclusion
        if lines[-1] != conclusion:
            raise error.ProofError(f'conclusion {lines[-1]} does not match expected {conclusion}')
        proof = Sequent(name, premises, conclusion)
        if name is not None:
            self.session.register(proof)
        return proof, statements  # TODO: remove

    @v_args(meta=True)
    @_errorswithcontext
    def deduction(self, args, meta):
        f, tag, justification = args
        is_premise, is_assumption = False, False
        if justification[0] == 'premise':
            is_premise = True
        elif justification[0] == 'assumption':
            is_assumption = True
            self.session.ctx().push()
        elif justification[0] == 'copy':
            if not f == justification[1][0]:
                raise error.DeductionError('different formulae', justification[1], f, 'copy')
        else:
            try:
                self.session.apply(justification[0], justification[1], f)
            except error.LogicError as e:
                raise error.DeductionError(e, justification[1], f, justification[0])
            # else conclusion is ok

        self.session.ctx().nextline(f, tag, premise=is_premise, assumption=is_assumption)
        return args  # TODO remove?

    def assumption(self, args):
        deductions, _ = self.session.ctx().pop()
        tag, *objs = args
        box = self.session.ctx().addbox(deductions, tag)
        return box, objs  # TODO remove?

    @v_args(meta=True)
    @_errorswithcontext
    def axiom(self, args, meta):
        ax = Sequent(args[0], args[1][0], args[1][1])
        self.session.register(ax)
        return ax

    def __ref_helper(self, ref):
        if isinstance(ref, Tag):
            return self.session.ctx().getline(self.session.ctx().gettag(ref))
        else:
            return self.session.ctx().getline(ref)
    @v_args(meta=True)
    @_errorswithcontext
    def ref(self, args, meta):
        ref = args[0]
        if ref is Last:
            rv = self.session.ctx().lastline()
        elif ref is LastLast:
            rv = self.session.ctx().lastline(2)
        else:
            rv = self.__ref_helper(ref)
        if rv is None or not isinstance(rv, WFF):
            raise error.ReferenceMissingError(f'proof line {ref} non-existent or out of scope')
        return rv
    @v_args(meta=True)
    @_errorswithcontext
    def blockref(self, args, meta):
        ref = args[0]
        if ref is Last:
            rv = self.session.ctx().lastbox()
        elif ref is LastLast:
            rv = self.session.ctx().lastbox(2)
        else:
            rv = self.__ref_helper(ref)
        if rv is None:
            raise error.ReferenceMissingError(f'no subproof at proof line {ref}')
        if not isinstance(rv, Box):
            raise error.ReferenceMissingError('[..] but last line not end of subproof')
        return rv
    tag = lambda self, t: Tag(t[0])
    last = lambda self, t: Last
    lastlast = lambda self, t: LastLast

    _implies = lambda self, t: WFF(Connective.IMPLIES, *t)
    _or = lambda self, t: WFF(Connective.OR, *t)
    _and = lambda self, t: WFF(Connective.AND, *t)
    _not = lambda self, t: WFF(Connective.NOT, None, t[0])
    _falsum = lambda self, _: WFF(Falsum, None, None)
    atom = lambda self, s: WFF(Atom(s[0][0]), None, None)

    sequent = lambda self, fs: (fs[:-1] if fs[0] is not None else [], fs[-1])
    rule = sequent
    box = lambda self, fs: Box(*fs)
    justification = lambda self, fs: (fs[0], fs[1:])
    premisejustification = lambda self, _: ('premise', None)
    assumptionjustification = lambda self, _: ('assumption', None)
    copyjustification = lambda self, f: ('copy', f)

    identifier = lambda self, ss: ''.join(ss)
    symnot = lambda self, _: '¬'
    symand = lambda self, _: '∧'
    symor = lambda self, _: '∨'
    symimplies = lambda self, _: '→'
    symfalsum = lambda self, _: '⊥'


class Tag(str):
    pass
Last = Tag('..')
LastLast = Tag('...')
