from dataclasses import dataclass
from enum import Enum
from typing import List, Union
from . import error


@dataclass
class Sequent:
    __slots__ = ('name', 'premises', 'conclusion', 'slots')
    name: str
    premises: List[Union['WFF', 'Box', 'Substitution']]
    conclusion: Union['WFF', 'Substitution']
    slots: List[str]
    def __str__(self):
        return ('{' + ' '.join(self.slots) + '} ' if self.slots else '') + ', '.join(str(p) for p in self.premises) + ' ⊢ ' + str(self.conclusion)
    def __repr__(self):
        return f'Sequent<{self.name}: {str(self)}>'
    def apply(self, premises: List[Union['WFF', 'Box']], conclusion: 'WFF', slots: List['Term'] = None):
        if len(premises) != len(self.premises):
            raise error.MismatchRuleError(f'wrong number of premises: got {len(premises)}, expected {len(self.premises)}')
        slots = slots if slots is not None else []
        if len(slots) != len(self.slots):
            raise error.MismatchRuleError(f'wrong number of slotted terms: got {len(slots)}, expected {len(self.slots)}')
        atoms = {}
        terms = {k: slots[i] for i, k in enumerate(self.slots)}
        for i, pr in enumerate(premises):
            if isinstance(self.premises[i], Box) and not isinstance(pr, Box):
                raise error.MismatchRuleError(f'wrong type of premise #{i+1} {pr}: expected box')
            if not self.premises[i].contains(pr, atoms=atoms, terms=terms, premise=True):
                raise error.MismatchRuleError(
                    f'inapplicable premise #{i+1} {pr} to {self.premises[i]} (expands to {self.premises[i].expand(atoms, terms)})')
        if not self.conclusion.contains(conclusion, atoms=atoms, terms=terms):
            raise error.MismatchRuleError(
                f'inapplicable conclusion to {self.conclusion} (expands to {self.conclusion.expand(atoms, terms)})')


@dataclass
class Box:
    __slots__ = ('assumption', 'conclusion', 'variable')
    assumption: 'WFF'
    conclusion: 'WFF'
    variable: Union[str, None]
    def __str__(self):
        if self.variable is None:
            return f'[{str(self.assumption)}...{str(self.conclusion)}]'
        else:
            return f'[{{{self.variable}}} {str(self.assumption)}...{str(self.conclusion)}]'
    def contains(self, other: 'Box', **kwargs):
        terms = kwargs.setdefault('terms', {})
        if self.variable is not None:
            if other.variable is None:
                return False
            terms[self.variable] = other.variable
        elif other.variable is not None:
            return False
        if self.assumption is None:
            return other.assumption is None and self.conclusion.contains(other.conclusion, **kwargs)
        else:
            return self.assumption.contains(other.assumption, **kwargs) and self.conclusion.contains(other.conclusion, **kwargs)
    def expand(self, atom_table, term_table):
        if self.variable is not None:
            if self.variable in term_table:
                var = term_table[self.variable]
            else:
                var = self.variable + "'"
        else:
            var = None
        ass = self.assumption.expand(atom_table, term_table) if self.assumption is not None else None
        con = self.conclusion.expand(atom_table, term_table)
        return Box(ass, con, var)


@dataclass
class Substitution:
    __slots__ = ('atom', 'new', 'old')
    atom: 'Atom'
    new: str
    old: str
    def __str__(self):
        return f'{str(self.atom)}[{str(self.new)}/{str(self.old)}]'
    def contains(self, other, **kwargs):
        atoms = kwargs.setdefault('atoms', {})
        terms = kwargs.setdefault('terms', {})
        premise = kwargs.setdefault('premise', False)
        if premise and self.atom not in atoms:
            # Backwards substitution: formula introduced here, replace indicated term in other by dummy for use
            try:
                new = terms[self.new]
            except KeyError:
                raise error.SubstitutionError(f'attempted to bw substitute for unknown term {self.new} (does your rule {str(self)} need a slot?)')
            if self.old in terms:
                raise error.SubstitutionError(f'attempted to bw substitute when term {self.old} known as {terms[self.old]} (i.e. rule incorrectly defined)')
            sub_vars = set(new.walk_vars()) if isinstance(new, Term) else set(new)
            terms[self.old] = self.old + "'"
            atoms[self.atom] = other.substitute(new, self.old + "'", sub_vars)
            return True  # note we set containing here
        else:
            # Forward substitution: general formula known, check for match
            # Conclusion substitution: straightforward replacement, all elements known, check for match
            try:
                wff = atoms[self.atom]
            except KeyError:
                raise error.SubstitutionError(f'attempted to substitute in unknown formula in expression {str(self)}')
            try:
                old = terms[self.old]
                new = terms[self.new]
            except KeyError as e:
                raise error.SubstitutionError(f'attempted to substitute with unknown term {e.args[0]} in expression {str(wff)}[{str(self.old)}/{str(self.new)}]')
            sub_vars = set(new.walk_vars()) if isinstance(new, Term) else set(new)
            wff = wff.substitute(old, new, sub_vars)
            return wff == other  # note equality and not containment because we substitute in proof set of formulas
    def expand(self, atom_table, term_table):
        if self.atom not in atom_table:
            return self.atom + "'"
        old = term_table.get(self.old, self.old + "'")
        new = term_table.get(self.new, self.new + "'")
        sub_vars = set(new.walk_vars()) if isinstance(new, Term) else set(new)
        return atom_table[self.atom].substitute(old, new, sub_vars)


@dataclass
class WFF:
    """Well-formed formula."""
    __slots__ = ('node', 'left', 'right')
    node: Union['Connective', 'Quantification', type('Falsum'), 'Predicate']
    left: Union['WFF', None]
    right: Union['WFF', None]

    '''
    def __eq__(self, other):
        """Checks if two well-formed formulas are exactly equal."""
        if not isinstance(other, WFF):
            return False
        return self.node == other.node and self.left == other.left and self.right == other.right
    '''

    def contains(self, other, **kwargs) -> bool:
        """Checks if another well-formed formula is semantically contained in the well-formed formula"""
        atoms = kwargs.setdefault('atoms', {})
        terms = kwargs.setdefault('terms', {})
        if not isinstance(other, WFF):
            return False
        if isinstance(self.node, Equality):
            if not isinstance(other.node, Equality):
                return False
            return _compare_or_set(terms, self.node.terms[0], other.node.terms[0]) and _compare_or_set(terms, self.node.terms[1], other.node.terms[1])
        elif isinstance(self.node, Predicate):
            # New predicate
            # TODO is this too restrictive?
            if not isinstance(other.node, Predicate) or len(self.node.terms) != len(other.node.terms):
                return False
            if not _compare_or_set(atoms, self.node.atom, other):
                return False
            return all(_compare_or_set(terms, left, other.node.terms[i]) for i, left in enumerate(self.node.terms))
        elif isinstance(self.node, Atom):
            # New atom
            return _compare_or_set(atoms, self.node, other)
        elif self.node is Falsum:
            return other.node is Falsum
        elif self.left is None:
            if isinstance(self.node, Quantification):
                if not isinstance(other.node, Quantification) or not self.node.quantifier == other.node.quantifier:
                    return False
                if terms.get(self.node.variable, '').endswith("'") and isinstance(self.right.node, Atom):
                    # We had an undefined substitution for some variable, which we now know
                    old = terms[self.node.variable]
                    terms[self.node.variable] = other.node.variable
                    atoms[self.right.node] = atoms[self.right.node].substitute(old, other.node.variable, set(other.node.variable))
                elif not _compare_or_set(terms, self.node.variable, other.node.variable):
                    return False
                return self.right.contains(other.right, **kwargs)
            else:
                return self.node == other.node and self.right.contains(other.right, **kwargs)
        else:
            return self.node == other.node and self.left.contains(other.left, **kwargs) and self.right.contains(other.right, **kwargs)

    def expand(self, atom_table, term_table):
        if isinstance(self.node, Predicate):
            try:
                node = atom_table[self.node.atom]
            except KeyError:
                node = Predicate(Atom(self.node.atom + "'"), [term_table.get(t, t + "'") for t in self.node.terms])
        elif isinstance(self.node, Atom):
            try:
                node = atom_table[self.node]
            except KeyError:
                node = Atom(self.node + "'")
        else:
            node = self.node
        left = self.left.expand(atom_table, term_table) if self.left is not None else None
        right = self.right.expand(atom_table, term_table) if self.right is not None else None
        return WFF(node, left, right)

    def substitute(self, old, new, sub_vars):
        if isinstance(self.node, Predicate):
            node = self.node.substitute(old, new, sub_vars)
        elif isinstance(self.node, Quantification):
            if self.node.variable == old:
                if not isinstance(new, str):
                    raise error.LogicError(f'attempted to substitute non-variable {new} for quantifier variable {old}')
                node = Quantification(self.node.quantifier, new)
            elif self.node.variable in sub_vars:
                raise error.FreeBoundError(new, str(self), f'substituting for {old}')
            else:
                node = self.node
        else:
            node = self.node
        left = self.left.substitute(old, new, sub_vars) if self.left is not None else None
        right = self.right.substitute(old, new, sub_vars) if self.right is not None else None
        return WFF(node, left, right)
    def walk_vars(self):
        if isinstance(self.node, Predicate):
            yield from self.node.walk_vars()
        elif isinstance(self.node, Quantification):
            yield self.node.variable
        if self.left is not None:
            yield from self.left.walk_vars()
        if self.right is not None:
            yield from self.right.walk_vars()

    def __repr__(self):
        return 'WFF<' + str(self) + '>'
    def __str__(self):
        if self.left is None and self.right is None:
            return str(self.node)
        elif self.left is None:
            return str(self.node) + str(self.right)
        else:
            return '(' + str(self.left) + ' ' + str(self.node) + ' ' + str(self.right) + ')'


class Connective(Enum):
    IMPLIES = '→'
    OR = '∨'
    AND = '∧'
    NOT = '¬'
    def __str__(self):
        return self.value


class Quantifier(Enum):
    FORALL = '∀'
    EXISTS = '∃'
    def __str__(self):
        return self.value

@dataclass
class Quantification:
    __slots__ = ('quantifier', 'variable')
    quantifier: Quantifier
    variable: str
    def __str__(self):
        return f'{str(self.quantifier)}{str(self.variable)}'


@dataclass
class Predicate:
    __slots__ = ('atom', 'terms')
    atom: 'Atom'
    terms: List[Union[str, 'Term']]
    def __str__(self):
        return f'{self.atom}({",".join(str(s) for s in self.terms)})'
    def _substitute(self, old, new, sub_vars):
        terms = self.terms.copy()
        for i, t in enumerate(terms):
            if t == old and not getattr(t, 'protected', False):
                terms[i] = new
            elif isinstance(t, Term):
                terms[i] = t.substitute(old, new, sub_vars)
        return terms
    def substitute(self, old, new, sub_vars):
        return Predicate(self.atom, self._substitute(old, new, sub_vars))
    def has_var(self, var):
        return any(t == var or (isinstance(t, Term) and t.has_var(var)) for t in self.terms)
    def walk_vars(self):
        for t in self.terms:
            if isinstance(t, Term):
                yield from t.walk_vars()
            else:
                yield t

class Equality(Predicate):
    def __init__(self, left, right):
        super().__init__(Atom('='), [left, right])
    def __str__(self):
        return f'{str(self.terms[0])} = {str(self.terms[1])}'
    def substitute(self, old, new, sub_vars):
        terms = self._substitute(old, new, sub_vars)
        return Equality(terms[0], terms[1])


@dataclass
class Term:
    __slots__ = ('name', 'args', 'protected')
    name: str
    args: List['Term']
    protected: bool
    def __str__(self):
        return f'{self.name}({",".join(str(s) for s in self.args)})'
    def __repr__(self):
        return f"'{str(self)}'"
    def __add__(self, other):
        return Term(self.name + other, self.args, self.protected)
    def __eq__(self, other):
        if not isinstance(other, Term):
            return False
        return self.name == other.name and self.args == other.args
    def substitute(self, old, new, sub_vars):
        args = self.args.copy()
        for i, t in enumerate(args):
            if t == old and not getattr(t, 'protected', False):
                args[i] = new
            elif isinstance(t, Term):
                args[i] = t.substitute(old, new, sub_vars)
        return Term(self.name, args, False)
    def has_var(self, var):
        return any(t == var or (isinstance(t, Term) and t.has_var(var)) for t in self.args)
    def walk_vars(self):
        for t in self.args:
            if isinstance(t, Term):
                yield from t.walk_vars()
            else:
                yield t

class ProtectedVariable(str):
    protected = True
    pass

class Atom(str):
    pass

class FalsumType:
    __slots__ = ()
    def __repr__(self):
        return '⊥'
Falsum = FalsumType()


def _compare_or_set(d: dict, reference, other) -> bool:
    if reference not in d:
        d[reference] = other
        return True
    return d[reference] == other
