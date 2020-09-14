from typing import Union

class ContextualLogicError(Exception):
    def __init__(self, base: 'LogicError', file: str, line: int, col: int, meta=None):
        super().__init__(f'{file}:{line}:{col}: {base}')
class LogicError(Exception):
    def __init__(self, message: str):
        super().__init__('error: ' + message)
class LogicWarning(Warning):
    pass

class SyntaxError(LogicError):
    def __init__(self, got: str, expected: str):
        # TODO
        super().__init__(f'')
class DeductionError(LogicError):
    def __init__(self, error: Union[LogicError, str], premises: [str], conclusion: str, rule: str):
        super().__init__(f'cannot deduce {str(conclusion)} by {rule} using premises\n\t{", ".join(str(p) for p in premises)}\n\t{str(error)}')
class UnknownRuleError(LogicError):
    def __init__(self, rule: str):
        super().__init__(f'unknown rule {rule}')
class MismatchRuleError(LogicError):
    def __init__(self, comment: str):
        super().__init__(comment)
class ProofError(LogicError):
    def __init__(self, comment: str):
        super().__init__(comment)
class InvalidJustificationError(LogicError):
    def __init__(self, type: str, details: str = None):
        super().__init__(f'cannot introduce {type} here{": " + details if details is not None else ""}')
class MissingJustificationError(LogicError):
    def __init__(self, type: str, details: str = None):
        super().__init__(f'missing {type} in scope{": " + details if details is not None else ""}')
class CircularIncludeError(LogicError):
    def __init__(self, offender: str):
        self.offender = offender
        super().__init__(f'circular include of {offender}')
class NameCollisionError(LogicError):
    def __init__(self, name: str):
        super().__init__(f'name collision: {name}')

class ReferenceError(LogicError):
    pass
class ReferenceMissingError(ReferenceError):
    def __init__(self, help: str):
        super().__init__(f'missing reference: {help}')
class ReferenceTagCollisionError(ReferenceError):
    def __init__(self, tag: str, old: int, new: int):
        super().__init__(f'tag collision: @{tag} (already proof line {old} before {new})')
