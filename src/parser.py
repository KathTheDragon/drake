from dataclasses import dataclass, field, InitVar
from .lexer import Lexer
from .parsetree import *

## Exceptions
class InvalidSyntax(Exception):
    def __init__(self, token=None):
        if token is not None:
            super().__init__(f'{token.value} @ {token.linenum}:{token.column}')

## Parser
@dataclass
class Parser(Lexer):
    def error(self, token=None):
        if token is None:
            token = self._peek()
        raise InvalidSyntax(token)

    def peek(self, kind=None, *values):
        token = self._peek()
        if kind is None:
            return token
        elif token.kind != kind:
            return False
        elif not values:
            return token
        elif token.value not in values:
            return False
        else:
            return token

    def maybe(self, kind=None, *values):
        if self.peek(kind, *values):
            return self._next()
        else:
            return False

    def next(self, kind=None, *values):
        if self.peek(kind, *values):
            return self._next()
        else:
            self.error()

    ## Helpers
    def itemlist(self, itemfunc, lookahead):
        if self.maybe(lookahead):
            return []
        else:
            return self._itemlist(itemfunc(), itemfunc, lookahead)

    def _itemlist(self, item, itemfunc, lookahead):
        if self.maybe(lookahead):
            return [item]
        elif self.peek('NEWLINE'):
            return self._separateditems(item, itemfunc, 'NEWLINE', lookahead)
        elif self.peek('COMMA'):
            return self._separateditems(item, itemfunc, 'COMMA', lookahead)
        else:
            self.error()

    def _separateditems(self, item, itemfunc, separator, lookahead):
        items = [item]
        while True:
            if self.maybe(separator):
                if self.maybe(lookahead):
                    return items
                else:
                    items.append(itemfunc())
            elif self.maybe(lookahead):
                return items
            else:
                self.error()

    def leftop(self, operand, *ops):
        left = operand()
        while True:
            if self.peek('OPERATOR', *ops):
                op = self.next().value
                right = operand()
                left = BinaryOpNode(left, op, right)
            else:
                return left

    def rightop(self, operand, *ops):
        left = operand()
        if self.peek('OPERATOR', *ops):
            op = self.next().value
            right = self.rightop(ops, operand)
            return BinaryOpNode(left, op, right)
        else:
            return left

    ## States
    def parse(self):
        program = ModuleNode(self.itemlist(self.expression, 'EOF'))
        return program

    def expression(self):
        if self.peek('KEYWORD'):
            keyword = self.peek().value
            func = {
                'if': self.if_,
                'case': self.case,
                'try': self.try_,
                'for': self.for_,
                'while': self.while_,
                'iter': self.iter,
                'do': self.do,
                'object': self.object,
                'enum': self.enum,
                'module': self.module,
                'exception': self.exception,
                'mutable': self.mutable,
                'throw': self.throw,
                'return': self.return_,
                'yield': self.yield_,
                'break': self.break_,
                'continue': self.continue_,
                'pass': self.pass_,
            }.get(keyword, None)
            if func is not None:
                return func()
            elif keyword in ('nonlocal', 'const'):
                if self.peek('OPERATOR', '<'):
                    typehint, name = self.typedname()
                    return self.assignment(TargetNode(keyword, typehint, name))
                else:
                    name = self.identifier()
                    return self.assignment(TargetNode(keyword, None, name))
            else:
                self.error()
        elif self.peek('OPERATOR'):
            operator = self.peek().value
            if operator == '<':
                typehint, name = self.typedname()
                if self.peek('ASSIGNMENT'):
                    return self.assignment(TargetNode('local', typehint, name))
                elif self.peek('LAMBDA'):
                    return self.lambda_([VParamNode(False, typehint, name)])
                elif self.maybe('COLON'):
                    value = self.expression()
                    return self.lambda_([KwParamNode(False, typehint, name, value)])
                else:
                    return DeclarationNode(False, typehint, name)
            elif operator in ('*', '**'):
                if operator == '*':
                    cls = VParamNode
                else:
                    cls = KwParamNode
                self.next()
                typehint, name = self.typedname()
                param = cls(True, typehint, name)
                return self.lambda_([param])
            elif operator in ('-', '!', 'not'):
                return self.unary()
        elif self.peek('LBRACKET'):
            return self.bracketexpr()
        elif self.peek('LBRACE'):
            return self.brace()
        elif self.peek('LSQUARE'):
            return self.list()
        elif self.peek('IDENTIFIER'):
            name = self.identifier()
            if self.peek('ASSIGNMENT'):
                return self.assignment(name)
            elif self.peek('LAMBDA'):
                return self.lambda_([name])
            else:
                return name
        else:
            return self.literal()

    def bracketexpr(self):
        self.next('LBRACKET')
        if self.maybe('RBRACKET'):
            return self.dispatchbracketitems([])
        else:
            item = self.bracketitem()
            if self.maybe('RBRACKET'):
                return self.dispatchbracketitems(item)
            else:
                items = self._itemlist(item, self.bracketitem, 'RBRACKET')
                return self.dispatchbracketitems(items)

    def dispatchbracketitems(self, items):
        if self.peek('ASSIGNMENT'):
            if isinstance(items, list):
                return self.assignment(items)
            else:
                return self.assignment([item])
        elif self.peek('LAMBDA'):
            if isinstance(items, list):
                return self.lambda_(items)
            else:
                return self.lambda_([item])
        elif isinstance(items, list):
            for item in items:
                if isinstance(item, (TargetNode, VParamNode, KwParamNode)):
                    self.error()
            return TupleNode(items)
        else:
            if isinstance(items, (TargetNode, VParamNode, KwParamNode)):
                self.error()
            return GroupingNode(items)

    def bracketitem(self):
        if self.peek('KEYWORD', 'nonlocal', 'const'):
            keyword = self.next().value
            if self.peek('OPERATOR', '<'):
                typehint, name = self.typedname()
            else:
                typehint, name = None, self.identifier()
            return TargetNode(keyword, typehint, name)
        elif self.peek('OPERATOR', '*', '**'):
            if operator == '*':
                cls = VParamNode
            else:
                cls = KwParamNode
            self.next()
            typehint, name = self.typedname()
            return cls(True, typehint, name)
        elif self.peek('OPERATOR', '<'):
            typehint, name = self.typedname()
            if self.peek('COLON'):
                value = self.expression()
                return KwParamNode(False, typehint, name, value)
            else:
                return DeclarationNode(False, typehint, name)
        else:
            return self.expression()

    def assignment(self, targets):
        if isinstance(targets, list):
            targets = [self.checktarget(target) for target in targets]
        else:
            targets = self.checktarget(targets)
        op = self.next('ASSIGNMENT')
        value = self.expression()
        return AssignmentNode(targets, op, value)

    def checktarget(self, target):
        if isinstance(target, TargetNode):
            return target
        elif isinstance(target, DeclarationNode):
            return TargetNode('local', target.typehint, target.name)
        elif isinstance(target, IdentifierNode):
            return TargetNode('local', None, target)
        else:
            self.error()

    def lambda_(self, params):
        _params = []
        # This should probably enforce parameter ordering too
        for param in params:
            if isinstance(param, (VParamNode, KwParamNode)):
                _params.append(param)
            elif isinstance(param, DeclarationNode):
                _params.append(VParamNode(False, param.typehint, param.name))
            else:
                self.error()
        self.next('LAMBDA')
        body = self.expression()
        return LambdaNode(_params, [], body)

    def typedname(self):
        self.next('OPERATOR', '<')
        typehint = self.type()
        self.next('OPERATOR', '>')
        name = self.identifier()
        return typehint, name

    def type(self):
        name = self.identifier()
        if self.maybe('LSQUARE'):
            params = self.itemlist(self.type, 'RSQUARE')
        else:
            params = []
        return TypeNode(name, params)

    def if_(self):
        self.next('KEYWORD', 'if')
        condition = self.expression()
        self.next('KEYWORD', 'then')
        iftrue = self.expression()
        if self.maybe('KEYWORD', 'else'):
            iffalse = self.expression()
        else:
            iffalse = None
        return IfNode(condition, iftrue, iffalse)

    def case(self):
        self.next('KEYWORD', 'case')
        value = self.expression()
        self.next('OPERATOR', 'in')
        mapping = self.expression()
        if self.maybe('KEYWORD', 'else'):
            default = self.expression()
        else:
            default = None
        return CaseNode(value, mapping, default)

    def try_(self):
        self.next('KEYWORD', 'try')
        expression = self.expression()
        if self.peek('KEYWORD', 'catch'):
            ... # Catch route
        elif self.maybe('KEYWORD', 'finally'):
            catches = []
            final = self.expression()
        else:
            self.error()
        return TryNode(expression, catches, final)

    def for_(self):
        self.next('KEYWORD', 'for')
        if self.maybe('LBRACKET'):
            vars = self.itemlist(self.identifier, 'RBRACKET')
        else:
            vars = self.identifier()
        self.next('OPERATOR', 'in')
        container = self.expression()
        body = self.block()
        return ForNode(vars, container, body)

    def while_(self):
        self.next('KEYWORD', 'while')
        condition = self.expression()
        body = self.block()
        return WhileNode(condition, body)

    def iter(self):
        self.next('KEYWORD', 'iter')
        if self.peek('LSQUARE'):
            iterable = self.list()
        elif self.peek('KEYWORD', 'for'):
            iterable = self.for_()
        elif self.peek('KEYWORD', 'while'):
            iterable = self.while_()
        else:
            self.error()
        return IterNode(iterable)

    def do(self):
        self.next('KEYWORD', 'do')
        return DoNode(self.block())

    def object(self):
        self.next('KEYWORD', 'object')
        return ObjectNode(self.block())

    def enum(self):
        self.next('KEYWORD', 'enum')
        if self.maybe('KEYWORD', 'flags'):
            flags = True
        else:
            flags = False
        self.next('LBRACE')
        return EnumNode(flags, self.itemlist(self.enumitem, 'RBRACE'))

    def enumitem(self):
        name = self.identifier()
        if self.maybe('ASSIGNMENT', '='):
            value = self.number()
        else:
            value = None
        return EnumItemNode(name, value)

    def module(self):
        self.next('KEYWORD', 'module')
        return ModuleNode(self.block())

    def exception(self):
        self.next('KEYWORD', 'exception')
        return ExceptionNode(self.block())

    def mutable(self):
        self.next('KEYWORD', 'mutable')
        if self.peek('KEYWORD', 'object'):
            value = self.object()
        elif self.peek('LBRACE'):
            value = self.mapping()
        elif self.peek('LSQUARE'):
            value = self.list()
        elif self.peek('LBRACKET'):
            value = self.tuple()
        elif self.peek('STRING'):
            value = self.string()
        else:
            self.error()
        return MutableNode(value)

    def throw(self):
        self.next('KEYWORD', 'throw')
        return ThrowNode(self.expression())

    def return_(self):
        self.next('KEYWORD', 'return')
        return ReturnNode(self.expression())

    def yield_(self):
        self.next('KEYWORD', 'yield')
        if self.maybe('KEYWORD', 'from'):
            return YieldFromNode(self.expression())
        else:
            return YieldNode(self.expression())

    def break_(self):
        self.next('KEYWORD', 'break')
        return BreakNode()

    def continue_(self):
        self.next('KEYWORD', 'continue')
        return ContinueNode()

    def pass_(self):
        self.next('KEYWORD', 'pass')
        return PassNode()

    def boolor(self):
        return self.rightop(self.boolxor, 'or')

    def boolxor(self):
        return self.rightop(self.booland, 'xor')

    def booland(self):
        return self.rightop(self.inclusion, 'and')

    def inclusion(self):
        left = self.identity()
        if self.maybe('OPERATOR', 'in'):
            right = self.inclusion()
            return BinaryOpNode(left, 'in', right)
        elif self.maybe('OPERATOR', 'not'):
            self.next('OPERATOR', 'in')
            right = self.inclusion()
            return BinaryOpNode(left, 'not in', right)
        else:
            return left

    def identity(self):
        left = self.comparison()
        if self.maybe('OPERATOR', 'is'):
            if self.maybe('OPERATOR', 'not'):
                op = 'is not'
            else:
                op = 'is'
            right = self.identity()
            return BinaryOpNode(left, op, right)
        else:
            return left

    def comparison(self):
        return self.rightop(self.bitor, '<', '<=', '>', '>=', '==', '!=')

    def bitor(self):
        return self.leftop(self.bitxor, '|')

    def bitxor(self):
        return self.leftop(self.bitand, '^')

    def bitand(self):
        return self.leftop(self.shift, '&')

    def shift(self):
        return self.leftop(self.addition, '<<', '>>')

    def addition(self):
        return self.leftop(self.product, '*', '/')

    def product(self):
        return self.leftop(self.modulus, '+', '-')

    def modulus(self):
        return self.leftop(self.exponent, '%')

    def exponent(self):
        return self.leftop(self.unary, '**')

    def unary(self):
        if self.peek('OPERATOR', 'not', '!', '-'):
            op = self.next()
            expr = self.unary()
            return UnaryOpNode(op, expr)
        else:
            return self.primary()

    def primary(self):
        obj = self.atom()
        while True:
            if self.maybe('DOT'):
                attr = self.identifier()
                obj = LookupNode(obj, attr)
            elif self.maybe('LBRACKET'):
                args = self.itemlist(self.arg, 'RBRACKET')
                obj = CallNode(obj, args)
            elif self.peek('LSQUARE'):
                subscript = self.list()
                obj = SubscriptNode(obj, subscript)
            else:
                return obj

    def arg(self):
        if self.peek('OPERATOR', '*', '**'):
            star = self.next()
            expr = self.expression()
            return UnaryOpNode(star, expr)
        elif self.peek('IDENTIFIER'):
            name = self.identifier()
            self.next('COLON')
            expr = self.expression()
            return KwargNode(name, expr)
        else:
            return self.expression()

    def atom(self):
        if self.peek('LBRACE'):
            return self.brace()
        elif self.peek('LSQUARE'):
            return self.list()
        elif self.peek('LBRACKET'):
            return self.bracket()
        elif self.peek('IDENTIFIER'):
            return self.identifier()
        else:
            return self.literal()

    def brace(self):
        self.next('LBRACE')
        if self.maybe('RBRACE'):
            return MappingNode()
        else:
            expr = self.expression()
            if self.maybe('COLON'):
                pair = PairNode(expr, self.expression())
                return MappingNode(self._itemlist(pair, self.pair, 'RBRACE'))
            else:
                return BlockNode(self._itemlist(expr, self.expression, 'RBRACE'))

    def mapping(self):
        self.next('LBRACE')
        return MappingNode(self.itemlist(self.pair, 'RBRACE'))

    def pair(self):
        key = self.expression()
        self.next('COLON')
        value = self.expression()
        return PairNode(key, value)

    def block(self):
        self.next('LBRACE')
        return BlockNode(self.itemlist(self.expression, 'RBRACE'))

    def list(self):
        self.next('LSQUARE')
        if self.maybe('RSQUARE'):
            return ListNode()
        else:
            expr = self.expression()
            if self.maybe('RANGE'):
                if self.maybe('RSQUARE'):
                    return RangeNode(expr)
                elif self.maybe('COMMA'):
                    step = self.unary()
                    return RangeNode(expr, step=step)
                else:
                    stop = self.expression()
                    if self.maybe('RSQUARE'):
                        return RangeNode(expr, stop)
                    elif self.maybe('COMMA'):
                        step = self.unary()
                        return RangeNode(expr, stop, step=step)
                    else:
                        self.error()
            else:
                return ListNode(self._itemlist(expr, self.expression, 'RSQUARE'))

    def bracket(self):
        self.next('LBRACKET')
        if self.maybe('RBRACKET'):
            return TupleNode()
        else:
            expr = self.expression()
            if self.maybe('RBRACKET'):
                return GroupingNode(expr)
            else:
                return TupleNode(self._itemlist(expr, self.expression, 'RBRACKET'))

    def grouping(self):
        self.next('LBRACKET')
        expr = self.expression()
        self.next('RBRACKET')
        return GroupingNode(expr)

    def tuple(self):
        self.next('LBRACKET')
        return TupleNode(self.expression, 'RBRACKET')

    def literal(self):
        if self.peek('STRING'):
            return self.string()
        elif self.peek('NUMBER'):
            return self.number()
        elif self.peek('BOOLEAN'):
            return self.boolean()
        elif self.peek('NONE'):
            return self.none()
        else:
            self.error()

    def string(self):
        return StringNode(self.next('STRING').value)

    def number(self):
        return NumberNode(self.next('NUMBER').value)

    def boolean(self):
        return BooleanNode(self.next('BOOLEAN').value)

    def none(self):
        self.next('NONE')
        return NoneNode()

    def identifier(self):
        return IdentifierNode(self.next('IDENTIFIER').value)
