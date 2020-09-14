from dataclasses import dataclass
from enum import Enum
from typing import List, Union
from . import error


@dataclass
class Sequent:
    name: str
    premises: List[Union['WFF', 'Box']]
    conclusion: 'WFF'
    def __str__(self):
        return ', '.join(str(p) for p in self.premises) + ' ⊢ ' + str(self.conclusion)
    def __repr__(self):
        return f'Sequent<{self.name}: {str(self)}>'
    def apply(self, premises: List[Union['WFF', 'Box']], conclusion: 'WFF'):
        if len(premises) != len(self.premises):
            raise error.MismatchRuleError(f'wrong number of premises: got {len(premises)}, expected {len(self.premises)}')
        atom_table = {}
        for i, pr in enumerate(premises):
            if not isinstance(pr, type(self.premises[i])):
                raise error.MismatchRuleError(f'wrong type of premise #{i+1} {pr}: expected {"subproof" if isinstance(self.premises[i], Box) else "formula"}')
            if not self.premises[i].contains(pr, atom_table):
                raise error.MismatchRuleError(
                    f'inapplicable premise #{i+1} {pr} to {self.premises[i]} (expands to {self.premises[i].expand(atom_table)})')
        if not self.conclusion.contains(conclusion, atom_table):
            raise error.MismatchRuleError(
                f'inapplicable conclusion to {self.conclusion} (expands to {self.conclusion.expand(atom_table)})')


@dataclass
class Box:
    assumption: 'WFF'
    conclusion: 'WFF'
    def __str__(self):
        return '[' + str(self.assumption) + '...' + str(self.conclusion) + ']'
    def contains(self, other: 'Box', atom_table=None):
        atom_table = {} if atom_table is None else atom_table
        return self.assumption.contains(other.assumption, atom_table) and self.conclusion.contains(other.conclusion, atom_table)


@dataclass
class WFF:
    """Well-formed formula."""
    node: Union['Connective', type('Falsum'), 'Atom']
    left: Union['WFF', None]
    right: Union['WFF', None]

    def __eq__(self, other):
        """Checks if two well-formed formulas are exactly equal."""
        if not isinstance(other, WFF):
            return False
        return self.node == other.node and self.left == other.left and self.right == other.right
    #def __hash__(self):
    #    return hash((self.node, self.left, self.right))

    def contains(self, other, atom_table=None) -> bool:
        """Checks if another well-formed formula is semantically contained in the well-formed formula"""
        atom_table = atom_table if atom_table is not None else dict()
        if not isinstance(other, WFF):
            return False
        if isinstance(self.node, Atom):
            # New atom
            if self.node in atom_table:
                return atom_table[self.node] == other
            else:
                atom_table[self.node] = other
                return True
        elif self.node is Falsum:
            return other.node is Falsum
        elif self.left is None:
            return self.node == other.node and self.right.contains(other.right, atom_table)
        else:
            return self.node == other.node and self.left.contains(other.left, atom_table) and self.right.contains(other.right, atom_table)

    def expand(self, atom_table):
        if isinstance(self.node, Atom):
            try:
                node = atom_table[self.node]
            except KeyError:
                node = Atom(self.node + "'")
        else:
            node = self.node
        left = self.left.expand(atom_table) if self.left is not None else None
        right = self.right.expand(atom_table) if self.right is not None else None
        return WFF(node, left, right)

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


class Atom(str):
    pass


class FalsumType:
    def __repr__(self):
        return '⊥'
Falsum = FalsumType()
