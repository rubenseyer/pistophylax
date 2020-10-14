from . import logic

def latex(evaled, buf, verbose=False):
    if isinstance(evaled, list):
        for i in evaled:
            if isinstance(i, list) and verbose:
                latex(i, buf, verbose)
                continue
            _proof(i, buf)
    else:
        _proof(evaled, buf)

def _proof(t, buf):
    if not isinstance(t, tuple):
        # axiom, ignore
        return
    buf.write(f'\section{{{t[0].name}}} % {str(t[0])}\n')
    buf.write(f'\\begin{{logicproof}}{{{__countboxes(t[1])}}}\n')
    _lines(t[1], buf)
    buf.write('\n\end{logicproof}\n\n')

def _lines(lines, buf, indent=0, first=True):
    for line in lines:
        if isinstance(line[0], logic.Box):
            if not first:
                if line[0].assumption is not None:
                    buf.write('\\\\\n')
                else:
                    buf.write('\\proofbr\n')
            buf.write(' '*indent + '\\begin{subproof}')
            if line[0].variable is not None:
                buf.write(f' \\fresh{{{line[0].variable}}}')
            if line[0].assumption is None:
                buf.write('&')
            else:
                buf.write('\n')
            _lines(line[1], buf, indent=indent + 2, first=line[0].assumption is not None)
            buf.write('\n' + ' '*indent + '\\end{subproof}\n')
            first = True
            continue
        if not first:
            buf.write('\\\\\n')
        first = False
        buf.write(' '*indent)
        buf.write(str(line[0]).translate(REWRITE_TRANS))
        buf.write(' & ')
        # justification
        (rule, slots, premises) = line[2]
        premises = [p[1] for p in premises] if premises is not None else None
        buf.write('\\(')
        if rule[0] in REWRITE_MAP:
            buf.write(REWRITE_MAP[rule[0]] + '\\text{')
        else:
            buf.write(f'\\text{{{rule[0]}')
        if rule[-1].isdigit():
            buf.write(f'{rule[1:-1]}}}_{{{rule[-1]}}}')
        else:
            buf.write(f'{rule[1:]}}}')
        if slots is not None:
            buf.write(f'({", ".join(str(s) for s in slots)})')
        buf.write(f'\\) ')
        if premises is not None:
            buf.write(', '.join((f'{ll[0]}--{ll[1]}' if isinstance(ll, tuple) else str(ll)) for ll in premises))


REWRITE_MAP = {
    '¬': r'\lnot{}',
    '∧': r'\land{}',
    '∨': r'\lor{}',
    '→': r'\to{}',
    '⊥': r'\bot{}',
    '∀': r'\forall{}',
    '∃': r'\exists{}',
    '=': r'='
}
REWRITE_TRANS = str.maketrans(REWRITE_MAP)

def __countboxes(lines):
    c = 0
    for line in lines:
        if not isinstance(line[0], logic.Box):
            continue
        c = max(c, 1 + __countboxes(line[1]))
    return c
