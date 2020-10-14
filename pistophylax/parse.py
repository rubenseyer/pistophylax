from typing import TYPE_CHECKING
from lark import Lark, Transformer as BaseTransformer, v_args
from lark.exceptions import VisitError
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources
from .logic import *
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
        return self.session.load(args[0][1:-1], rel=self.session.path)

    @v_args(meta=True)
    @_errorswithcontext
    def proof(self, args, meta):
        name, (premises, conclusion), *statements = args
        # pop context
        if not self.session.ctx().is_top():
            raise error.ProofError('unclosed boxes at proof end')
        lines, premisecount, _ = self.session.ctx().pop()
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
        proof = Sequent(name, premises, conclusion, [])
        if name is not None:
            self.session.register(proof)
        return proof, statements  # TODO: remove

    @v_args(meta=True)
    @_errorswithcontext
    def deduction(self, args, meta):
        f, tag, (rule, slots, premises) = args
        premises = [p[0] for p in premises] if premises is not None else None
        is_premise, is_assumption = False, False
        if rule == 'premise':
            is_premise = True
        elif rule == 'assumption':
            is_assumption = True
        elif rule == 'copy':
            if not len(premises) == 1:
                raise error.DeductionError('wrong number of arguments', premises, f, 'copy')
            if not f == premises[0]:
                raise error.DeductionError('different formulae', premises, f, 'copy')
        else:
            try:
                self.session.apply(rule, premises, f, slots)
            except error.LogicError as e:
                raise error.DeductionError(e, premises, f, rule)
            # else conclusion is ok

        self.session.ctx().nextline(f, tag, premise=is_premise, assumption=is_assumption)
        return args  # TODO remove?

    @v_args(meta=True)
    @_errorswithcontext
    def block(self, args, meta):
        deductions, _, can_assume = self.session.ctx().pop()
        keyword, variable, tag, *objs = args
        box = self.session.ctx().addbox(deductions, variable, tag, can_assume)
        return box, objs  # TODO remove?
    def assume(self, _):
        self.session.ctx().push()
        return 'assume'
    def var(self, _):
        self.session.ctx().push(can_assume=False)
        return 'var'

    @v_args(meta=True)
    @_errorswithcontext
    def axiom(self, args, meta):
        ax = Sequent(args[0], args[2][0], args[2][1], args[1] if args[1] is not None else [])
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
            rv, i = self.session.ctx().lastline()
        elif ref is LastLast:
            rv, i = self.session.ctx().lastline(2)
        else:
            rv, i = self.__ref_helper(ref)
        if rv is None or not isinstance(rv, WFF):
            raise error.ReferenceMissingError(f'proof line {ref} non-existent or out of scope (did you mean to refer to a block?)')
        return rv, i
    @v_args(meta=True)
    @_errorswithcontext
    def blockref(self, args, meta):
        ref = args[0]
        if ref is Last:
            rv, i = self.session.ctx().lastbox()
        elif ref is LastLast:
            rv, i = self.session.ctx().lastbox(2)
        else:
            rv, i = self.__ref_helper(ref)
        if rv is None:
            raise error.ReferenceMissingError(f'no subproof at proof line {ref}')
        if not isinstance(rv, Box):
            raise error.ReferenceMissingError('[..] but last line not end of subproof')
        return rv, i
    tag = lambda self, t: Tag(t[0])
    last = lambda self, t: Last
    lastlast = lambda self, t: LastLast

    _implies = lambda self, t: WFF(Connective.IMPLIES, *t)
    _or = lambda self, t: WFF(Connective.OR, *t)
    _and = lambda self, t: WFF(Connective.AND, *t)
    _not = lambda self, t: WFF(Connective.NOT, None, t[0])
    _forall = lambda self, t: WFF(Quantification(Quantifier.FORALL, t[0]), None, t[1])
    _exists = lambda self, t: WFF(Quantification(Quantifier.EXISTS, t[0]), None, t[1])
    _falsum = lambda self, _: WFF(Falsum, None, None)
    _equals = lambda self, t: WFF(Equality(t[0], t[1]), None, None)
    atom = lambda self, s: WFF(Atom(s[0][0]), None, None)
    predicate = lambda self, s: WFF(Predicate(Atom(s[0][0]), s[1:]), None, None) if len(s) > 1 else WFF(Predicate(Atom(s[0][0]), list(s[0][1:])), None, None)
    variable = lambda self, s: ''.join(s)
    term = lambda self, s: Term(s[0][0], s[1:-1], s[-1] is not None)
    term_variable = lambda self, t: t[0] if t[1] is None else ProtectedVariable(t[0])
    substitution = lambda self, s: Substitution(Atom(s[0][0]), *s[1:])

    sequent = lambda self, fs: (fs[:-1] if fs[0] is not None else [], fs[-1])
    slots = lambda self, v: v
    box = lambda self, fs: Box(fs[1], fs[2], fs[0])
    justification = lambda self, fs: (fs[0], fs[1], fs[2:])
    premise_just = lambda self, _: ('premise', None, None)
    assumption_just = lambda self, _: ('assumption', None, None)
    copy_just = lambda self, f: ('copy', None, f)

    identifier = lambda self, ss: ''.join(ss)
    not_char = lambda self, _: '¬'
    and_char = lambda self, _: '∧'
    or_char = lambda self, _: '∨'
    implies_char = lambda self, _: '→'
    falsum_char = lambda self, _: '⊥'
    forall_char = lambda self, _: '∀'
    exists_char = lambda self, _: '∃'
    equals_char = lambda self, _: '='


class Tag(str):
    pass
Last = Tag('..')
LastLast = Tag('...')
