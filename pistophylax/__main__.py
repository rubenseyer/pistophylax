"""Pistophylax Natural deduction assistant

Usage:
  pistophylax [-v | --verbose] [--] [FILE | -]...
  pistophylax (-h | --help)

With no FILE, or when FILE is -, read standard input.

Options:
  -v --verbose  verbose output (report successes)
  -h --help     show this

"""

import logging
import sys
import time
from docopt import docopt
from lark.exceptions import VisitError
from .context import Session
from .error import ContextualLogicError, LogicError

def main():
    arguments = docopt(__doc__)
    verbose = arguments['--verbose']
    logging.basicConfig(format='%(message)s', level=logging.DEBUG if verbose else logging.INFO)
    inputs = arguments['FILE']

    tic = time.perf_counter_ns()
    success = True
    s = Session(debug=verbose)
    try:
        for path in inputs:
            if path == '-':
                s.eval(sys.stdin.read(), name='stdin')
            else:
                s.load(path)
    except VisitError as e:
        success = False
        if isinstance(e.orig_exc, (ContextualLogicError, LogicError)):
            logging.error(e.orig_exc)
        else:
            raise
    except (ContextualLogicError, LogicError) as e:
        success = False
        logging.error(e)
    delta = time.perf_counter_ns() - tic
    if delta > 5e8:
        duration = f'{delta*1e-9:.3f} s'
    else:
        duration = f'{delta*1e-6:.3f} ms'
    if success:
        logging.info(f'-- deduced {len(s.table)} in {duration}')
    else:
        logging.info(f'-- failed after {duration}')


main()
