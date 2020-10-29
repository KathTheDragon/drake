from dataclasses import dataclass, field, InitVar
from . import lexer
from .parsetree import *

## Exceptions
class InvalidSyntax(Exception):
    def __init__(self, token=None):
        if token is not None:
            super().__init__(f'{token.value} @ {token.linenum}:{token.column}')

## Parser
@dataclass
class Parser(lexer.Lexer):
    def error(self, token=None):
        if token is None:
            token = self._peek()
        raise InvalidSyntax(token)

    def peek(self, *kinds):
        token = self._peek()
        if not kinds or token.kind in kinds:
            return token
        else:
            return False

    def maybe(self, *kinds):
        token = self._peek()
        if not kinds or token.kind in kinds:
            return self._next()
        else:
            return False

    def next(self, *kinds):
        token = self._peek()
        if not kinds or token.kind in kinds:
            return self._next()
        else:
            self.error()

    ## Helpers
    def itemlist(self, itemfunc, lookahead, forcelist=True):
        if self.maybe(lookahead):
            return []
        else:
            return self._itemlist(itemfunc(), itemfunc, lookahead, forcelist)

    def _itemlist(self, item, itemfunc, lookahead, forcelist=True):
        if self.maybe(lookahead):
            if forcelist:
                return [item]
            else:
                return item
        elif self.peek('NEWLINE'):
            items = self._separateditems(item, itemfunc, 'NEWLINE', lookahead)
            if not forcelist and len(items) == 1:
                return item
            else:
                return items
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
            if self.peek(*ops):
                op = self.next().value
                right = operand()
                left = self.binaryopnode(left, op, right)
            else:
                return left

    def rightop(self, operand, *ops):
        left = operand()
        if self.peek(*ops):
            op = self.next().value
            right = self.rightop(ops, operand)
            return self.binaryopnode(left, op, right)
        else:
            return left

    ## States
    def parse(self):
        return self.modulenode(self.itemlist(self.expression, 'EOF'))

    def expression(self):
        if self.peek('KW_CASE'):
            return self.case()
        elif self.peek('KW_CONST', 'KW_LET'):
            return self.declaration()
        elif self.peek('KW_DO'):
            return self.do()
        elif self.peek('KW_ENUM'):
            return self.enum()
        elif self.peek('KW_EXCEPTION'):
            return self.exception()
        elif self.peek('KW_FOR'):
            return self.for_()
        elif self.peek('KW_IF'):
            return self.if_()
        elif self.peek('KW_ITER'):
            return self.iter()
        elif self.peek('KW_MODULE'):
            return self.module()
        elif self.peek('KW_MUTABLE'):
            return self.mutable()
        elif self.peek('KW_OBJECT'):
            return self.object()
        elif self.peek('KW_RAISES'):
            return self.raises()
        elif self.peek('KW_THROW'):
            return self.throw()
        elif self.peek('KW_TRY'):
            return self.try_()
        elif self.peek('KW_WHILE'):
            return self.while_()
        elif self.peek('KW_YIELD'):
            return self.yield_()
        elif self.peek('OP_MULT', 'OP_POW', 'OP_LT'):
            return self.lambda_([self.param()])
        elif self.peek('OP_SUB', 'OP_INV', 'OP_NOT'):
            return self.unary()
        elif self.peek('LBRACKET'):
            return self.bracketexpr()
        else:
            return self.primary()

    def declaration(self):
        if self.maybe('KW_LET'):
            const = False
        elif self.maybe('KW_CONST'):
            const = True
        else:
            self.error()
        if self.maybe('LBRACKET'):
            targets = self.itemlist(self.target, 'RBRACKET', forcelist=False)
        else:
            targets = self.target()
        declaration = self.declarationnode(const, targets)
        if self.peek(*lexer.ASSIGNMENT):
            return self.assignment(declaration)
        else:
            return declaration

    def target(self):
        if self.peek('OP_LT'):
            typehint, name = self.typedname()
        else:
            typehint, name = None, self.identifier()

    def bracketexpr(self):
        self.next('LBRACKET')
        if self.maybe('RBRACKET'):
            return self._primary(self.tuplenode([]))
        elif self.peek('OP_MULT', 'OP_POW', 'OP_LT'):
            items = self.itemlist(self.param, 'RBRACKET')
            return self.lambda_(items)
        else:
            exprs = self.itemlist(self.expression, 'RBRACKET', forcelist=False)
            if isinstance(exprs, list):
                return self._primary(self.tuplenode(exprs))
            else:
                return self._primary(self.groupingnode(exprs))

    def assignment(self, declaration):
        op = self.next(*lexer.ASSIGNMENT).value
        value = self.expression()
        return self.assignmentnode(declaration, op, value)

    def lambda_(self, params):
        self.next('LAMBDA')
        body = self.expression()
        return self.lambdanode(params, [], body)

    def param(self):
        if self.maybe('OP_MULT'):
            return self.vparamnode(True, *self.typedname())
        elif self.maybe('OP_POW'):
            return self.kwparamnode(True, *self.typedname())
        elif self.peek('OP_LT'):
            typehint, name = self.typedname()
            if self.maybe('COLON'):
                value = self.expression()
                return self.kwparamnode(False, typehint, name, value)
            else:
                return self.vparamnode(False, typehint, name)
        else:
            self.error()

    def typedname(self):
        self.next('OP_LT')
        typehint = self.type()
        self.next('OP_GT')
        name = self.identifier()
        return typehint, name

    def type(self):
        name = self.identifier()
        if self.maybe('LSQUARE'):
            params = self.itemlist(self.type, 'RSQUARE')
        else:
            params = []
        return self.typenode(name, params)

    def if_(self):
        self.next('KW_IF')
        condition = self.expression()
        self.next('KW_THEN')
        iftrue = self.expression()
        if self.maybe('KW_ELSE'):
            iffalse = self.expression()
        else:
            iffalse = None
        return self.ifnode(condition, iftrue, iffalse)

    def case(self):
        self.next('KW_CASE')
        value = self.expression()
        self.next('OP_IN')
        mapping = self.expression()
        if self.maybe('KW_ELSE'):
            default = self.expression()
        else:
            default = None
        return self.casenode(value, mapping, default)

    def try_(self):
        self.next('KW_TRY')
        expression = self.expression()
        if self.peek('KW_CATCH'):
            ... # Catch route
        else:
            self.error()
        return self.trynode(expression, catches)

    def for_(self):
        self.next('KW_FOR')
        if self.maybe('LBRACKET'):
            vars = self.itemlist(self.identifier, 'RBRACKET')
        else:
            vars = self.identifier()
        self.next('OP_IN')
        container = self.expression()
        body = self.block()
        return self.fornode(vars, container, body)

    def while_(self):
        self.next('KW_WHILE')
        condition = self.expression()
        body = self.block()
        return self.whilenode(condition, body)

    def iter(self):
        self.next('KW_ITER')
        if self.peek('LSQUARE'):
            iterable = self.list()
        elif self.peek('KW_FOR'):
            iterable = self.for_()
        elif self.peek('KW_WHILE'):
            iterable = self.while_()
        else:
            self.error()
        return self.iternode(iterable)

    def do(self):
        self.next('KW_DO')
        return self.donode(self.block())

    def object(self):
        self.next('KW_OBJECT')
        return self.objectnode(self.block())

    def enum(self):
        self.next('KW_ENUM')
        if self.maybe('KW_FLAGS'):
            flags = True
        else:
            flags = False
        self.next('LBRACE')
        return self.enumnode(flags, self.itemlist(self.enumitem, 'RBRACE'))

    def enumitem(self):
        name = self.identifier()
        if self.maybe('OP_ASSIGN'):
            value = self.number()
        else:
            value = None
        return self.enumitemnode(name, value)

    def module(self):
        self.next('KW_MODULE')
        return self.modulenode(self.block())

    def exception(self):
        self.next('KW_EXCEPTION')
        return self.exceptionnode(self.block())

    def mutable(self):
        self.next('KW_MUTABLE')
        if self.peek('KW_OBJECT'):
            value = self.object()
        elif self.peek('KW_ITER'):
            value = self.iter()
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
        return self.mutablenode(value)

    def throw(self):
        self.next('KW_THROW')
        return self.thrownode(self.expression())

    def raises(self):
        self.next('KW_RAISES')
        self.next('LBRACKET')
        expression = self.expression()
        self.next('COMMA')
        exception = self.identifier()
        self.next('RBRACKET')
        return self.raisesnode(expression, exception)

    def yield_(self):
        self.next('KW_YIELD')
        if self.maybe('KW_FROM'):
            return self.yieldfromnode(self.expression())
        else:
            return self.yieldnode(self.expression())

    def boolor(self):
        return self.rightop(self.boolxor, 'OP_OR')

    def boolxor(self):
        return self.rightop(self.booland, 'OP_XOR')

    def booland(self):
        return self.rightop(self.inclusion, 'OP_AND')

    def inclusion(self):
        left = self.identity()
        if self.maybe('OP_IN'):
            right = self.inclusion()
            return self.binaryopnode(left, 'in', right)
        elif self.maybe('OP_NOT'):
            self.next('OP_IN')
            right = self.inclusion()
            return self.binaryopnode(left, 'not in', right)
        else:
            return left

    def identity(self):
        left = self.comparison()
        if self.maybe('OP_IS'):
            if self.maybe('OP_NOT'):
                op = 'is not'
            else:
                op = 'is'
            right = self.identity()
            return self.binaryopnode(left, op, right)
        else:
            return left

    def comparison(self):
        return self.rightop(self.bitor, *lexer.OP_COMP)

    def bitor(self):
        return self.leftop(self.bitxor, 'OP_BITOR')

    def bitxor(self):
        return self.leftop(self.bitand, 'OP_BITXOR')

    def bitand(self):
        return self.leftop(self.shift, 'OP_BITAND')

    def shift(self):
        return self.leftop(self.addition, 'OP_LSHIFT', 'OP_RSHIFT')

    def addition(self):
        return self.leftop(self.product, 'OP_MULT', 'OP_DIV')

    def product(self):
        return self.leftop(self.modulus, 'OP_ADD', 'OP_SUB')

    def modulus(self):
        return self.leftop(self.exponent, 'OP_MOD')

    def exponent(self):
        return self.leftop(self.unary, 'OP_POW')

    def unary(self):
        if self.peek('OP_SUB', 'OP_INV', 'OP_NOT'):
            op = self.next()
            expr = self.unary()
            return self.unaryopnode(op, expr)
        else:
            return self.primary()

    def primary(self):
        return self._primary(self.atom())

    def _primary(self, obj):
        while True:
            if self.maybe('DOT'):
                attr = self.identifier()
                obj = self.lookupnode(obj, attr)
            elif self.maybe('LBRACKET'):
                args = self.itemlist(self.arg, 'RBRACKET')
                obj = self.callnode(obj, args)
            elif self.peek('LSQUARE'):
                subscript = self.list()
                obj = self.subscriptnode(obj, subscript)
            else:
                return obj

    def arg(self):
        if self.peek('OP_MULT', 'OP_POW'):
            star = self.next()
            expr = self.expression()
            return self.unaryopnode(star, expr)
        elif self.peek('IDENTIFIER'):
            name = self.identifier()
            self.next('COLON')
            expr = self.expression()
            return self.kwargnode(name, expr)
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
            return self.mappingnode([])
        else:
            expr = self.expression()
            if self.maybe('COLON'):
                pair = self.pairnode(expr, self.expression())
                return self.mappingnode(self._itemlist(pair, self.pair, 'RBRACE'))
            else:
                return self.blocknode(self._itemlist(expr, self.expression, 'RBRACE'))

    def mapping(self):
        self.next('LBRACE')
        return self.mappingnode(self.itemlist(self.pair, 'RBRACE'))

    def pair(self):
        key = self.expression()
        self.next('COLON')
        value = self.expression()
        return self.pairnode(key, value)

    def block(self):
        self.next('LBRACE')
        return self.blocknode(self.itemlist(self.expression, 'RBRACE'))

    def list(self):
        self.next('LSQUARE')
        if self.maybe('RSQUARE'):
            return self.listnode([])
        else:
            expr = self.expression()
            if self.maybe('RANGE'):
                if self.maybe('RSQUARE'):
                    return self.rangenode(expr, None, None)
                elif self.maybe('COMMA'):
                    step = self.unary()
                    return self.rangenode(expr, None, step)
                else:
                    stop = self.expression()
                    if self.maybe('RSQUARE'):
                        return self.rangenode(expr, stop, None)
                    elif self.maybe('COMMA'):
                        step = self.unary()
                        return self.rangenode(expr, stop, step)
                    else:
                        self.error()
            else:
                return self.listnode(self._itemlist(expr, self.expression, 'RSQUARE'))

    def bracket(self):
        self.next('LBRACKET')
        exprs = self.itemlist(self.expression, 'RBRACKET', forcelist=False)
        if isinstance(exprs, list):
            return self.tuplenode(exprs)
        else:
            return self.groupingnode(exprs)

    def grouping(self):
        self.next('LBRACKET')
        expr = self.expression()
        self.next('RBRACKET')
        return self.groupingnode(expr)

    def tuple(self):
        self.next('LBRACKET')
        return self.tuplenode(self.expression, 'RBRACKET')

    def literal(self):
        if self.peek('STRING'):
            return self.string()
        elif self.peek('NUMBER'):
            return self.number()
        elif self.peek('BOOLEAN'):
            return self.boolean()
        elif self.peek('NONE'):
            return self.none()
        elif self.peek('BREAK'):
            return self.break_()
        elif self.peek('CONTINUE'):
            return self.continue_()
        elif self.peek('PASS'):
            return self.pass_()
        else:
            self.error()

    def string(self):
        return self.stringnode(self.next('STRING').value)

    def number(self):
        return self.numbernode(self.next('NUMBER').value)

    def boolean(self):
        return self.booleannode(self.next('BOOLEAN').value)

    def none(self):
        self.next('NONE')
        return self.nonenode()

    def break_(self):
        self.next('BREAK')
        return self.breaknode()

    def continue_(self):
        self.next('CONTINUE')
        return self.continuenode()

    def pass_(self):
        self.next('PASS')
        return self.passnode()

    def identifier(self):
        return self.identifiernode(self.next('IDENTIFIER').value)

    # Node functions

    def assignmentnode(self, declaration, operator, expression):
        return AssignmentNode(declaration, operator, expression)

    def declarationnode(self, const, targets):
        return DeclarationNode(const, targets)

    def targetnode(self, typehint, name):
        return TargetNode(typehint, name)

    def typenode(self, type, params):
        return TypeNode(type, params)

    def ifnode(self, condition, then, default):
        return IfNode(condition, then, default)

    def casenode(self, value, cases, default):
        return CaseNode(value, cases, default)

    def trynode(self, expression, catches):
        return TryNode(expression, catches)

    def catchnode(self, exception, name, expression):
        return CatchNode(exception, name, expression)

    def fornode(self, vars, container, body):
        return ForNode(vars, container, body)

    def whilenode(self, condition, body):
        return WhileNode(condition, body)

    def iternode(self, expression):
        return IterNode(expression)

    def donode(self, body):
        return DoNode(body)

    def objectnode(self, body):
        return ObjectNode(body)

    def enumnode(self, flags, items):
        return EnumNode(flags, items)

    def modulenode(self, body):
        return ModuleNode(body)

    def exceptionnode(self, body):
        return ExceptionNode(body)

    def mutablenode(self, expression):
        return MutableNode(expression)

    def thrownode(self, expression):
        return ThrowNode(expression)

    def yieldfromnode(self, expression):
        return YieldFromNode(expression)

    def yieldnode(self, expression):
        return YieldNode(expression)

    def lambdanode(self, vparams, kwparams, returns):
        return LambdaNode(vparams, kwparams, returns)

    def vparamnode(self, starred, typehint, name):
        return VParamNode(starred, typehint, name)

    def kwparamnode(self, starred, typehint, name, default):
        return KwParamNode(starred, typehint, name, default)

    def binaryopnode(self, left, operator, right):
        return BinaryOpNode(left, operator, right)

    def unaryopnode(self, operator, operand):
        return UnaryOpNode(operator, operand)

    def lookupnode(self, object, attribute):
        return LookupNode(object, attribute)

    def callnode(self, object, vargs, kwargs):
        return CallNode(object, vargs, kwargs)

    def kwargnode(self, name, value):
        return KwargNode(name, value)

    def subscriptnode(self, object, subscript):
        return SubcriptNode(object, subscript)

    def mappingnode(self, pairs):
        return MappingNode(pairs)

    def pairnode(self, key, value):
        return PairNode(key, value)

    def blocknode(self, expressions):
        return BlockNode(expressions)

    def listnode(self, expressions):
        return ListNode(expressions)

    def rangenode(self, start, stop, step):
        return RangeNode(start, stop, step)

    def groupingnode(self, expression):
        return GroupingNode(expression)

    def tuplenode(self, expressions):
        return TupleNode(expressions)

    def identifiernode(self, name):
        return IdentifierNode(name)

    def stringnode(self, value):
        return StringNode(value)

    def numbernode(self, value):
        return NumberNode(value)

    def boolnode(self, value):
        return BoolNode(value)

    def nonenode(self):
        return NoneNode()

    def breaknode(self):
        return BreakNode()

    def continuenode(self):
        return ContinueNode()

    def passnode(self):
        return PassNode()
