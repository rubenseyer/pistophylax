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
        self.table: Dict[str, Sequent] = dict()

        self.file: str = ''
        self.contents: str = ''
        self.path: Union[str, None] = None
        self.loaded: Dict[str, bool] = {}

        self.context: Union['Context', None] = None

    def load(self, path, rel=None):
        if not os.path.isabs(path) and rel is not None:
            path = os.path.join(os.path.dirname(rel), path)
        path = os.path.realpath(path)
        relpath = os.path.relpath(path)

        # star include
        if os.path.basename(path) == '*':
            return [self.load(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(os.path.dirname(path)) for filename in sorted(filenames)]

        if not self.loaded.get(path, True):
            raise error.CircularIncludeError(path)
        if self.loaded.get(path, False):
            logging.debug(f'include of already included {relpath}, ignoring')
            return None
        self.loaded[path] = False  # starting load
        try:
            with open(path, 'r', encoding='utf-8') as f:
                last = self.path
                self.path = path
                rv = self.eval(f.read(), name=relpath)
                self.path = last
        except OSError as e:
            raise error.LogicError(f'failed to include {relpath}: {str(e)}') from e
        self.loaded[path] = True  # finished load
        return rv

    def eval(self, txt, name='-'):
        logging.debug('evaluating ' + name)
        oldfile, self.file = self.file, name
        oldcontents, self.contents = self.contents, txt
        p = self.parser.parse(txt)
        rv = self.transformer.transform(p)
        self.file, self.contents = oldfile, oldcontents
        return rv

    def register(self, sq: Sequent):
        logging.debug(f'✓ {sq.name}: {str(sq)}')
        if sq.name in self.table:
            logging.warning(f'warning: {sq.name} as {str(sq)} overwrites {str(self.table[sq.name])}')
        self.table[sq.name] = sq

    def apply(self, name: str, premises: List[Union[WFF, Box]], conclusion: WFF, slots: List[Union[str, 'Term']] = None) -> WFF:
        try:
            return self.table[name].apply(premises, conclusion, slots)
        except KeyError:
            raise error.UnknownRuleError(name)

    def session(self):
        return self
    def ctx(self) -> 'Context':
        if self.context is None:
            self.context = Context(self, None, can_assume=False)
        return self.context


class Context:
    def __init__(self, session: Session, parent: Union['Context', None], can_assume=True):
        self._session = session
        self.parent = parent

        self.cur = self.parent.cur if self.parent is not None else 1

        self._lines: Dict[int, Union[WFF, 'Box']] = {}
        self._tags: Dict[str, int] = {}
        self._unfreshvars = parent._unfreshvars.copy() if parent is not None else set()
        self._bannedvars = parent._bannedvars.copy() if parent is not None else set()

        self._premisecount = 0
        self.can_assume = can_assume

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
                raise error.InvalidJustificationError('premise', 'inside box')
            if not self.is_first() and self._premisecount != (self.cur - 1):
                raise error.InvalidJustificationError('premise', 'not top of proof')
            self._premisecount += 1
        if assumption:
            if not self.can_assume:
                raise error.InvalidJustificationError('assumption', 'outside assumption box')
            if not self.is_first():
                raise error.InvalidJustificationError('assumption', 'not top of box')
        if self.can_assume and self.is_first() and not assumption:
            raise error.MissingJustificationError('assumption', 'must introduce at top')
        vars = set(wff.walk_vars())
        if vars & self._bannedvars:
            raise error.LogicError(f'rule application would cause fresh variable(s) {vars & self._bannedvars} to escape')
        self._unfreshvars |= vars
        self._lines[self.cur] = wff
        self.cur += 1
    def lastline(self, levels=1):
        return self.getline(self.cur - levels)
    def _lastitem(self, levels=1, recurse=True):
        if len(self._lines) < levels:
            if recurse and self.parent is not None:
                return self.parent._lastitem(levels)
            else:
                return (None, None)
        return list(self._lines.items())[-levels]
    def is_first(self):
        return not self._lines
    def is_top(self):
        return self.parent is None

    def addbox(self, lines, variable=None, tag=None, can_assume=True):
        try:
            first, firstv = next(iter(lines.items()))
        except StopIteration:
            raise error.LogicError(f'subproof must have at least one line (otherwise it may be omitted)')
        last, lastv = list(lines.items())[-1]
        i = self.cur - last + first - 1
        last_row_num, _ = self._lastitem()
        if last_row_num is None:
            last_row_num = 0
        if i <= last_row_num:
            raise error.LogicError(f'wrong number of lines in box? {repr((last, lastv, i, last_row_num, not self.is_first() and i <= last_row_num))}')
        if variable in self._unfreshvars:
            raise error.LogicError(f'alleged fresh variable {variable} already in use')
        box = Box(firstv if can_assume else None, lastv, variable)
        self._lines[i] = box
        if variable is not None:
            self._unfreshvars.add(variable)
            self._bannedvars.add(variable)
        if tag is not None:
            self._addtag(tag, i)
        return box
    def lastbox(self, levels=1):
        return self._lastitem(levels, recurse=False)[1]

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
    def push(self, can_assume=True):
        ctx = Context(self._session, self, can_assume=can_assume)
        self._session.context = ctx
        return ctx
    def pop(self):
        self._session.context = self.parent
        if not self.is_top():
            self.parent.cur = self.cur
        return self._lines, self._premisecount, self.can_assume
