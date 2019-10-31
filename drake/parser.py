from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Tuple, Union
from .ast import *
from .ast import Precedence
from .lexer import Token, lex

## Constants
EOF = Token('EOF', 'eof', 0, 0)
LITERAL = (
    'STRING',
    'INTEGER',
    'DECIMAL',
    'IMAG_INTEGER',
    'IMAG_DECIMAL',
    'BOOLEAN',
    'NONE'
)
Values = Union[str, Tuple[str]]

## Exceptions
class DrakeSyntaxError(Exception):
    def __init__(self, error, token):
        value = token.value
        linenum = token.linenum
        column = token.column
        super().__init__(f'{error}: {value!r} @ {linenum}:{column}')
        self.error = error
        self.value = value
        self.linenum = linenum
        self.column = column

def expectedToken(expected, token):
    return DrakeSyntaxError(f'expected {expected!r}', token)

def unexpectedToken(token):
    return DrakeSyntaxError(f'unexpected {token.type.lower()}', token)

class DrakeCompilerWarning(Warning):
    def __init__(self, warning, token):
        value = token.value
        linenum = token.linenum
        column = token.column
        super().__init__(f'{warning}: {value} @ {linenum}:{column}')
        self.warning = warning
        self.value = value
        self.linenum = linenum
        self.column = column

## Classes
@dataclass
class DescentParser:
    source: str
    tokens: Iterator[Token] = field(init=False, default=iter([]))
    current: Token = field(init=False, default=EOF)
    log: List[Exception] = field(init=False, default_factory=list)

    # Basic token functions
    def advance(self) -> None:
        try:
            self.current = next(self.tokens)
        except StopIteration:
            pass

    def matches(self, type: Values, value: Values=()) -> bool:
        if isinstance(type, str):
            if self.current.type != type:
                return False
        else:
            if self.current.type not in type:
                return False
        if isinstance(value, str):
            return self.current.value == value
        elif value:
            return self.current.value in value
        else:
            return True

    def consume(self, type: Values, value: Values=()) -> None:
        if self.matches(type, value):
            self.advance()
        else:
            raise expectedToken(value or type, self.current)

    # Pattern functions
    def leftassoc(self, func: Callable, operator: Values) -> ASTNode:
        expr = func()
        while self.matches('OPERATOR', operator):
            op = self.current
            self.advance()
            right = func()
            expr = BinaryOpNode(expr, op, right)
        return expr

    def rightassoc(self, func: Callable, operator: Values) -> ASTNode:
        expr = func()
        if not self.matches('OPERATOR', operator):
            return expr
        op = self.current
        self.advance()
        right = self.rightassoc(func, operator)
        return BinaryOpNode(expr, op, right)

    def list(self, func: Callable, endtype: str, endvalue: Values=()) -> List[ASTNode]:
        expressions = []
        if self.matches('NEWLINE'):
            self.advance()
        if self.matches(endtype, endvalue):
            return expressions
        try:
            expressions.append(func())
        except DrakeSyntaxError as e:
            self.log.append(e)
            while not self.matches(('NEWLINE', 'COMMA', endtype)):
                self.advance()
        if self.matches(endtype, endvalue):
            return expressions
        delimiter = self.current.type
        newline = None
        while self.matches(delimiter):
            self.advance()
            if self.matches(endtype, endvalue):
                return expressions
            if newline is None:
                newline = self.matches('NEWLINE')
            if newline:
                self.consume('NEWLINE')
            try:
                expressions.append(func())
            except DrakeSyntaxError as e:
                self.log.append(e)
                while not self.matches((delimiter, endtype)):
                    self.advance()
        if self.matches('NEWLINE'):
            self.advance()
        return expressions

    # Parsing functions
    def parse(self) -> BlockNode:
        self.tokens = lex(self.source)
        self.advance()
        self.log = []
        program = self.list(self.parseAssignment, 'EOF')
        self.consume('EOF')
        return BlockNode(program)

    def parsePairList(self) -> List[ASTNode]:
        return self.list(self.parsePair, 'RBRACKET')

    def parsePair(self) -> ASTNode:
        expr = self.parseAssignment()
        if not self.matches('COLON'):
            return expr
        if isinstance(expr, AssignmentNode):
            self.log.append(DrakeSyntaxError('cannot use assignment as a pair key', self.current))
        self.advance()
        value = self.parseExpression()
        return PairNode(expr, value)

    def parseAssignList(self) -> List[ASTNode]:
        return self.list(self.parseAssignment, 'RBRACKET')

    def parseAssignment(self) -> ASTNode:
        if self.matches('KEYWORD', ('nonlocal', 'const')):
            mode = self.current
            self.advance()
            target = self.parseExpression()
            if not self.matches('ASSIGNMENT'):
                self.log.append(unexpectedToken(mode))
                return target
            mode = mode.value
        else:
            mode = ''
            target = self.parseExpression()
            if not self.matches('ASSIGNMENT'):
                return target
        if not isinstance(target, IdentifierNode):
            # Need to fix this to use a more useful token
            self.log.append(DrakeSyntaxError('invalid target for assignment', self.current))
        operator = self.current
        self.advance()
        expression = self.parseAssignment()
        if operator.value != '=':
            operator.type = 'OPERATOR'
            expression = BinaryOpNode(target, operator, expression)
        if isinstance(expression, (LambdaNode, ClassNode, ExceptionNode)) and mode != 'const':
            # Need to fix this to use a more useful token
            self.log.append(DrakeCompilerWarning(f'{expression.nodetype.lower()} should be assigned to a constant', operator))
        return AssignmentNode(mode, target, expression)

    def parseExprList(self) -> List[ASTNode]:
        return self.list(self.parseExpression, 'RBRACKET')

    def parseExpression(self) -> ASTNode:
        return self.parseKeyword()

    def parseKeyword(self) -> ASTNode:
        if self.matches('KEYWORD', 'return'):
            self.advance()
            return ReturnNode(self.parseFlow())
        elif self.matches('KEYWORD', 'yield'):
            self.advance()
            return YieldNode(self.parseFlow())
        elif self.matches('KEYWORD', 'yield from'):
            self.advance()
            return YieldFromNode(self.parseFlow())
        elif self.matches('KEYWORD', 'break'):
            self.advance()
            return BreakNode()
        elif self.matches('KEYWORD', 'continue'):
            self.advance()
            return ContinueNode()
        elif self.matches('KEYWORD', 'multi'):
            keyword = self.current
            self.advance()
            block = self.parseBlock()
            for expr in block:
                if not isinstance(expr, LambdaNode):
                    self.log.append(DrakeSyntaxError(f'invalid multimethod', keyword))
            return MultimethodNode(list(block))
        elif self.matches('KEYWORD', 'class'):
            keyword = self.current
            self.advance()
            constructor = self.parseLambda()
            return ClassNode(constructor.params, constructor.returns)
        else:
            return self.parseFlow()

    def parseFlow(self) -> ASTNode:
        if self.matches('KEYWORD', 'if'):
            self.advance()
            condition = self.parseFlow()
            self.consume('KEYWORD', 'then')
            then = self.parseFlow()
            if self.matches('KEYWORD', 'else'):
                self.advance()
                default = self.parseFlow()
            else:
                default = None
            return IfNode(condition, then, default)
        elif self.matches('KEYWORD', 'case'):
            self.advance()
            value = self.parseCall()
            self.consume('OPERATOR', 'in')
            cases = self.parseFlow()
            if self.matches('KEYWORD', 'else'):
                self.advance()
                default = self.parseFlow()
            else:
                default = None
            return CaseNode(value, cases, default)
        elif self.matches('KEYWORD', 'for'):
            self.advance()
            vars = self.list(self.parseTypehint, 'OPERATOR', 'in')
            for var in vars:
                if isinstance(var, TypehintNode):
                    var = var.expr
                if not isinstance(var, IdentifierNode):
                    self.log.append(DrakeSyntaxError('invalid loop variable', self.current))
            self.consume('OPERATOR', 'in')
            container = self.parseFlow()
            body = self.parseBlock()
            return ForNode(vars, container, body)
        elif self.matches('KEYWORD', 'while'):
            self.advance()
            condition = self.parseFlow()
            body = self.parseBlock()
            return WhileNode(condition, body)
        else:
            return self.parseLambda()

    def parseLambda(self) -> ASTNode:
        expression = self.parseBoolOr()
        if not self.matches('LAMBDA'):
            return expression
        if isinstance(expression, GroupingNode):
            params = [expression.expr]
        elif isinstance(expression, TupleNode):
            params = expression.items
        else:
            params = [expression]
        errors = []
        for param in params:
            if isinstance(param, AssignmentNode):
                self.log.pop()
            elif not isinstance(param, IdentifierNode):
                # Need to fix this to use a more useful token
                errors.append(DrakeSyntaxError('invalid lambda argument', self.current))
        self.log.extend(errors)
        self.advance()
        returns = self.parseLambda()
        return LambdaNode(params, returns)

    def parseBoolOr(self) -> ASTNode:
        return self.rightassoc(self.parseBoolXor, 'or')

    def parseBoolXor(self) -> ASTNode:
        return self.rightassoc(self.parseBoolAnd, 'xor')

    def parseBoolAnd(self) -> ASTNode:
        return self.rightassoc(self.parseComparison, 'and')

    def parseComparison(self) -> ASTNode:
        return self.leftassoc(self.parseRange, ('in','not in','is','is not','==','!=','<','<=','>','>='))

    def parseRange(self) -> ASTNode:
        left = self.parseBitOr()
        if not self.matches('OPERATOR', '..'):
            return left
        operator = self.current
        self.advance()
        right = self.parseBitOr()
        return BinaryOpNode(left, operator, right)

    def parseBitOr(self) -> ASTNode:
        return self.leftassoc(self.parseBitXor, '|')

    def parseBitXor(self) -> ASTNode:
        return self.leftassoc(self.parseBitAnd, '^')

    def parseBitAnd(self) -> ASTNode:
        return self.leftassoc(self.parseBitShift, '&')

    def parseBitShift(self) -> ASTNode:
        return self.leftassoc(self.parseAdd, ('<<', '>>'))

    def parseAdd(self) -> ASTNode:
        return self.leftassoc(self.parseMult, ('+', '-'))

    def parseMult(self) -> ASTNode:
        return self.leftassoc(self.parseExp, ('*', '/', '%'))

    def parseExp(self) -> ASTNode:
        return self.rightassoc(self.parseTypehint, '**')

    def parseTypehint(self) -> ASTNode:
        if self.matches('OPERATOR', '<'):
            self.advance()
            typehint = self.parseType()
            self.consume('OPERATOR', '>')
            return TypehintNode(typehint, self.parseUnary())
        else:
            return self.parseUnary()

    def parseType(self) -> TypeNode:
        type = self.current
        self.consume('IDENTIFIER')
        if self.matches('LBRACKET', '['):
            params = self.list(self.parseType, 'RBRACKET')
            self.consume('RBACKET', ']')
        else:
            params = []
        return TypeNode(type, params)

    def parseUnary(self) -> ASTNode:
        if not self.matches('OPERATOR', ('not', '!', '-', "*", "**")):
            return self.parseCall()
        operator = self.current
        self.advance()
        operand = self.parseUnary()
        return UnaryOpNode(operator, operand)

    def parseCall(self) -> ASTNode:
        expr = self.parsePrimary()
        while True:
            if self.matches('DOT'):
                self.advance()
                if not self.matches('IDENTIFIER'):
                    raise DrakeSyntaxError('expected identifier', self.current)
                attribute = IdentifierNode(self.current)
                self.advance()
                expr = LookupNode(expr, attribute)
            elif self.matches('LBRACKET', '('):
                self.advance()
                arguments = self.parseAssignList()
                self.consume('RBRACKET', ')')
                expr = CallNode(expr, arguments)
            elif self.matches('LBRACKET', '['):
                self.advance()
                subscript = self.parseExprList()
                self.consume('RBRACKET', ']')
                expr = SubscriptNode(expr, subscript)
            else:
                return expr

    def parsePrimary(self) -> ASTNode:
        if self.matches('LBRACKET', '('):
            self.advance()
            items = self.parseAssignList()
            if len(items) == 1:
                if not self.matches('COMMA'):
                    expr = items[0]
                    if isinstance(expr, AssignmentNode):
                        # Need to fix this to use a more useful token
                        self.log.append(DrakeSyntaxError('cannot put assignment inside grouping', self.current))
                    self.consume('RBRACKET', ')')
                    return GroupingNode(expr)
                self.advance()
            for item in items:
                if isinstance(item, AssignmentNode):
                    # Need to fix this to use a more useful token
                    self.log.append(DrakeSyntaxError('cannot put assignment inside tuple', self.current))
            self.consume('RBRACKET', ')')
            return TupleNode(items)
        elif self.matches('LBRACKET', '['):
            self.advance()
            items = self.parseExprList()
            self.consume('RBRACKET', ']')
            return ListNode(items)
        elif self.matches('LBRACKET', '{'):
            self.advance()
            items = self.parsePairList()
            if all(isinstance(item, PairNode) for item in items):
                self.consume('RBRACKET', '}')
                return MapNode(items)
            for item in items:
                if isinstance(item, PairNode):
                    # Need to fix this to use a more useful token
                    self.log.append(DrakeSyntaxError('cannot put pairing inside block', self.current))
            self.consume('RBRACKET', '}')
            return BlockNode(items)
        elif self.matches(LITERAL):
            expr = LiteralNode(self.current)
            self.advance()
            return expr
        elif self.matches('IDENTIFIER'):
            expr = IdentifierNode(self.current)
            self.advance()
            return expr
        else:
            raise unexpectedToken(self.current)
