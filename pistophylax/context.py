import logging
from typing import List, Dict, Set, Union
import os
from .parse import Transformer, init_parser
from .logic import Sequent, Box, WFF
from . import error

class Session:
    def __init__(self, debug=False):
        self.transformer = Transformer(self)
        self.parser = init_parser(debug=debug)
        self.table: Dict[str, Union[Axiom, Proof]] = dict()

        self.file: str = ''
        self.contents: str = ''
        self.loaded: Set[str] = set()

        self.context: Union['Context', None] = None

    def load(self, path):
        relpath = os.path.relpath(path)
        path = os.path.realpath(path)
        if path in self.loaded:
            raise error.CircularIncludeError(path)
        else:
            self.loaded.add(path)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return self.eval(f.read(), name=relpath)
        except OSError as e:
            raise error.LogicError(f'failed to include {relpath}: {str(e)}') from e

    def eval(self, txt, name='-'):
        oldfile, self.file = self.file, name
        oldcontents, self.contents = self.contents, txt
        rv = self.transformer.transform(self.parser.parse(txt))
        self.file, self.contents = oldfile, oldcontents
        return rv

    def register(self, sq: Sequent):
        logging.debug(f'✓ {sq.name}: {str(sq)}')
        self.table[sq.name] = sq

    def apply(self, name: str, premises: List[Union[WFF, Box]], conclusion: WFF) -> WFF:
        try:
            return self.table[name].apply(premises, conclusion)
        except KeyError:
            raise error.UnknownRuleError(name)

    def session(self):
        return self
    def ctx(self) -> 'Context':
        if self.context is None:
            self.context = Context(self, None)
        return self.context


class Context:
    def __init__(self, session: Session, parent: Union['Context', None]):
        self._session = session
        self.parent = parent

        self.cur = self.parent.cur if self.parent is not None else 1

        self._lines: Dict[int, Union[WFF, 'Box']] = {}
        self._tags: Dict[str, int] = {}

        self._premisecount = 0

    def getline(self, i):
        i = int(i)
        if i in self._lines:
            return self._lines[i]
        elif self.parent is not None:
            return self.parent.getline(i)
        else:
            return None
    def nextline(self, wff, tag=None, premise=False, assumption=False):
        if tag is not None:
            self._addtag(tag, self.cur)
        if premise:
            if not self.is_top():
                raise error.InvalidJustificationError('premise', 'inside assumption box')
            if not self.is_first() and self._premisecount != (self.cur - 1):
                raise error.InvalidJustificationError('premise', 'not top of proof')
            self._premisecount += 1
        if assumption:
            if self.is_top():
                raise error.InvalidJustificationError('assumption', 'outside assumption box')
            if not self.is_first():
                raise error.InvalidJustificationError('assumption', 'not top of box')
        if not self.is_top() and self.is_first() and not assumption:
            raise error.MissingJustificationError('assumption', 'must introduce at top')
        self._lines[self.cur] = wff
        self.cur += 1
    def lastline(self, levels=1):
        return self.getline(self.cur - levels)
    def is_first(self):
        return not self._lines
    def is_top(self):
        return self.parent is None

    def addbox(self, lines, tag=None):
        first = next(iter(lines.keys()))
        last = _dict_last_item(lines)[0]
        i = self.cur - last + first - 1
        if (self.is_first() and i != 1) or (not self.is_first() and i <= _dict_last_item(self._lines)[0]):
            raise error.LogicError('wrong number of lines in box?')
        box = Box(next(iter(lines.values())), _dict_last_item(lines)[1])
        self._lines[i] = box
        if tag is not None:
            self._addtag(tag, i)
        return box
    def lastbox(self, levels=1):
        if len(self._lines) < levels:
            return None
        return _dict_last_item(self._lines, levels)[1]

    def gettag(self, name):
        if name in self._tags:
            return self._tags[name]
        elif self.parent is not None:
            return self.parent.gettag(name)
        else:
            return None
    def _addtag(self, name, i):
        i = int(i)
        collision = self.gettag(name)
        if collision is not None:
            raise error.ReferenceTagCollisionError(name, collision, i)
        self._tags[name] = i

    def session(self):
        return self._session
    def push(self):
        ctx = Context(self._session, self)
        self._session.context = ctx
        return ctx
    def pop(self):
        self._session.context = self.parent
        if not self.is_top():
            self.parent.cur = self.cur
        return self._lines, self._premisecount

def _dict_last_item(d, i=1):
    return list(d.items())[-i]
