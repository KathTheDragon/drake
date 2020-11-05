from dataclasses import dataclass, field, InitVar
from . import lexer
from .parsetree import *

## Exceptions
class InvalidSyntax(Exception):
    def __init__(self, token, message=''):
        if message:
            super().__init__(f'{message} {token.value} @ {token.linenum}:{token.column}')
        else:
            super().__init__(f'{token.value} @ {token.linenum}:{token.column}')

## Parser
@dataclass
class Parser(lexer.Lexer):
    def error(self, token=None, message=''):
        if token is None:
            token = self._peek()
        raise InvalidSyntax(token, message)

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

    def next(self, *kinds, message=''):
        token = self._peek()
        if not kinds or token.kind in kinds:
            return self._next()
        else:
            if not message:
                message = f'expected {kinds}, got'
            self.error(message=message)

    ## Helpers
    def itemlist(self, itemfunc, lookahead, forcelist=True, **kwargs):
        if self.maybe(lookahead):
            return []
        else:
            return self._itemlist(itemfunc(), itemfunc, lookahead, forcelist, **kwargs)

    def _itemlist(self, item, itemfunc, lookahead, forcelist=True, **kwargs):
        if self.maybe(lookahead):
            if forcelist:
                return [item]
            else:
                return item
        elif self.peek('NEWLINE'):
            items = self._separateditems(item, itemfunc, 'NEWLINE', lookahead, **kwargs)
            if not forcelist and len(items) == 1:
                return item
            else:
                return items
        elif self.peek('COMMA'):
            return self._separateditems(item, itemfunc, 'COMMA', lookahead, **kwargs)
        else:
            self.error()

    def _separateditems(self, item, itemfunc, separator, lookahead, **kwargs):
        items = [item]
        while True:
            if self.maybe(separator):
                if self.maybe(lookahead):
                    return items
                else:
                    items.append(itemfunc(**kwargs))
            elif self.maybe(lookahead):
                return items
            else:
                self.error()

    def leftop(self, operand, *ops, **kwargs):
        left = operand(**kwargs)
        while True:
            if self.peek(*ops):
                op = self.next().value
                right = operand(**kwargs)
                left = self.binaryopnode(left, op, right, **kwargs)
            else:
                return left

    def rightop(self, operand, *ops, **kwargs):
        left = operand(**kwargs)
        if self.peek(*ops):
            op = self.next().value
            right = self.rightop(operand, *ops, **kwargs)
            return self.binaryopnode(left, op, right, **kwargs)
        else:
            return left

    ## States
    def parse(self, **kwargs):
        return self.modulenode(self.itemlist(self.expression, 'EOF', **kwargs), **kwargs)

    def expression(self, **kwargs):
        kind = self.peek().kind
        func = {
            'KW_CASE': self.case,
            'KW_CONST': self.declaration,
            'KW_LET': self.declaration,
            'KW_DO': self.do,
            'KW_ENUM': self.enum,
            'KW_EXCEPTION': self.exception,
            'KW_FOR': self.for_,
            'KW_IF': self.if_,
            'KW_ITER': self.iter,
            'KW_MODULE': self.module,
            'KW_MUTABLE': self.mutable,
            'KW_OBJECT': self.object,
            'KW_RAISES': self.raises,
            'KW_THROW': self.throw,
            'KW_TRY': self.try_,
            'KW_WHILE': self.while_,
            'OP_MULT': self.lambda_,
            'OP_POW': self.lambda_,
            'OP_LT': self.lambda_,
            'OP_SUB': self.unary,
            'OP_INV': self.unary,
            'OP_NOT': self.unary,
            'LBRACKET': self.bracketexpr
        }.get(kind, self.primary)
        return func(**kwargs)

    def declaration(self, **kwargs):
        if self.maybe('KW_LET'):
            const = False
        elif self.maybe('KW_CONST'):
            const = True
        else:
            self.error()
        if self.maybe('LBRACKET'):
            targets = self.itemlist(self.target, 'RBRACKET', forcelist=False, const=const, **kwargs)
        else:
            targets = self.target(const, **kwargs)
        declaration = self.declarationnode(const, targets, **kwargs)
        if self.peek(*lexer.ASSIGNMENT):
            return self.assignment(const, targets, **kwargs)
        else:
            return declaration

    def target(self, const, **kwargs):
        if self.peek('OP_LT'):
            typehint, name = self.typedname(**kwargs)
        else:
            typehint, name = None, self.name(**kwargs)
        return self.targetnode(const, typehint, name, **kwargs)

    def bracketexpr(self, **kwargs):
        self.next('LBRACKET')
        if self.maybe('RBRACKET'):
            return self._primary(self.tuplenode([], **kwargs), **kwargs)
        elif self.peek('OP_MULT', 'OP_POW', 'OP_LT'):
            items = self.itemlist(self.param, 'RBRACKET', **kwargs)
            return self.lambda_(items, **kwargs)
        else:
            exprs = self.itemlist(self.expression, 'RBRACKET', forcelist=False, **kwargs)
            if isinstance(exprs, list):
                return self._primary(self.tuplenode(exprs, **kwargs), **kwargs)
            else:
                return self._primary(self.groupingnode(exprs, **kwargs), **kwargs)

    def assignment(self, const, targets, **kwargs):
        if const:
            op = self.next('OP_ASSIGN',
                message='const assignment cannot be augmented:'
            ).value
        elif isinstance(targets, list):
            op = self.next('OP_ASSIGN',
                message='multiple assignment cannot be augmented:'
            ).value
        else:
            op = self.next(*lexer.ASSIGNMENT).value
        value = self.expression(**kwargs)
        return self.assignmentnode(const, targets, op, value, **kwargs)

    def lambda_(self, params=None, **kwargs):
        if params is None:
            params = [self.param(**kwargs)]
        self.next('LAMBDA')
        body = self.expression(**kwargs)
        return self.lambdanode(params, [], body, **kwargs)

    def param(self, **kwargs):
        if self.maybe('OP_MULT'):
            return self.vparamnode(True, *self.typedname(**kwargs), **kwargs)
        elif self.maybe('OP_POW'):
            return self.kwparamnode(True, *self.typedname(**kwargs), **kwargs)
        elif self.peek('OP_LT'):
            typehint, name = self.typedname(**kwargs)
            if self.maybe('COLON'):
                value = self.expression(**kwargs)
                return self.kwparamnode(False, typehint, name, value, **kwargs)
            else:
                return self.vparamnode(False, typehint, name, **kwargs)
        else:
            self.error()

    def typedname(self, **kwargs):
        self.next('OP_LT')
        typehint = self.type(**kwargs)
        self.next('OP_GT')
        name = self.name(**kwargs)
        return typehint, name

    def type(self, **kwargs):
        name = self.identifier(**kwargs)
        if self.maybe('LSQUARE'):
            params = self.itemlist(self.type, 'RSQUARE', **kwargs)
        else:
            params = []
        return self.typenode(name, params, **kwargs)

    def if_(self, **kwargs):
        self.next('KW_IF')
        condition = self.expression(**kwargs)
        self.next('KW_THEN')
        iftrue = self.expression(**kwargs)
        if self.maybe('KW_ELSE'):
            iffalse = self.expression(**kwargs)
        else:
            iffalse = None
        return self.ifnode(condition, iftrue, iffalse, **kwargs)

    def case(self, **kwargs):
        self.next('KW_CASE')
        value = self.expression(**kwargs)
        self.next('OP_IN')
        mapping = self.expression(**kwargs)
        if self.maybe('KW_ELSE'):
            default = self.expression(**kwargs)
        else:
            default = None
        return self.casenode(value, mapping, default, **kwargs)

    def try_(self, **kwargs):
        self.next('KW_TRY')
        expression = self.expression(**kwargs)
        if self.peek('KW_CATCH'):
            ... # Catch route
        else:
            self.error()
        return self.trynode(expression, catches, **kwargs)

    def for_(self, **kwargs):
        self.next('KW_FOR')
        if self.maybe('LBRACKET'):
            vars = self.itemlist(self.name, 'RBRACKET', **kwargs)
        else:
            vars = self.name(**kwargs)
        self.next('OP_IN')
        container = self.expression(**kwargs)
        body = self.block(**kwargs)
        return self.fornode(vars, container, body, **kwargs)

    def while_(self, **kwargs):
        self.next('KW_WHILE')
        condition = self.expression(**kwargs)
        body = self.block(**kwargs)
        return self.whilenode(condition, body, **kwargs)

    def iter(self, **kwargs):
        self.next('KW_ITER')
        if self.peek('LSQUARE'):
            iterable = self.list(**kwargs)
        elif self.peek('KW_FOR'):
            iterable = self.for_(**kwargs)
        elif self.peek('KW_WHILE'):
            iterable = self.while_(**kwargs)
        else:
            self.error()
        return self.iternode(iterable, **kwargs)

    def do(self, **kwargs):
        self.next('KW_DO')
        return self.donode(self.block(**kwargs), **kwargs)

    def object(self, **kwargs):
        self.next('KW_OBJECT')
        return self.objectnode(self.block(**kwargs), **kwargs)

    def enum(self, **kwargs):
        self.next('KW_ENUM')
        if self.maybe('KW_FLAGS'):
            flags = True
        else:
            flags = False
        self.next('LBRACE')
        return self.enumnode(flags, self.itemlist(self.enumitem, 'RBRACE', **kwargs), **kwargs)

    def enumitem(self, **kwargs):
        name = self.name(**kwargs)
        if self.maybe('OP_ASSIGN'):
            value = self.number(**kwargs)
        else:
            value = None
        return self.enumitemnode(name, value, **kwargs)

    def module(self, **kwargs):
        self.next('KW_MODULE')
        return self.modulenode(self.block(**kwargs), **kwargs)

    def exception(self, **kwargs):
        self.next('KW_EXCEPTION')
        return self.exceptionnode(self.block(**kwargs), **kwargs)

    def mutable(self, **kwargs):
        self.next('KW_MUTABLE')
        if self.peek('KW_OBJECT'):
            value = self.object(**kwargs)
        elif self.peek('KW_ITER'):
            value = self.iter(**kwargs)
        elif self.peek('LBRACE'):
            value = self.mapping(**kwargs)
        elif self.peek('LSQUARE'):
            value = self.list(**kwargs)
        elif self.peek('LBRACKET'):
            value = self.tuple(**kwargs)
        elif self.peek('STRING'):
            value = self.string(**kwargs)
        else:
            self.error()
        return self.mutablenode(value, **kwargs)

    def throw(self, **kwargs):
        self.next('KW_THROW')
        return self.thrownode(self.expression(**kwargs), **kwargs)

    def raises(self, **kwargs):
        self.next('KW_RAISES')
        self.next('LBRACKET')
        expression = self.expression(**kwargs)
        self.next('COMMA', 'NEWLINE')
        exception = self.identifier(**kwargs)
        self.maybe('COMMA', 'NEWLINE')
        self.next('RBRACKET')
        return self.raisesnode(expression, exception, **kwargs)

    def boolor(self, **kwargs):
        return self.rightop(self.boolxor, 'OP_OR', **kwargs)

    def boolxor(self, **kwargs):
        return self.rightop(self.booland, 'OP_XOR', **kwargs)

    def booland(self, **kwargs):
        return self.rightop(self.inclusion, 'OP_AND', **kwargs)

    def inclusion(self, **kwargs):
        left = self.identity(**kwargs)
        if self.maybe('OP_IN'):
            right = self.inclusion(**kwargs)
            return self.binaryopnode(left, 'in', right, **kwargs)
        elif self.maybe('OP_NOT'):
            self.next('OP_IN')
            right = self.inclusion(**kwargs)
            return self.binaryopnode(left, 'not in', right, **kwargs)
        else:
            return left

    def identity(self, **kwargs):
        left = self.comparison(**kwargs)
        if self.maybe('OP_IS'):
            if self.maybe('OP_NOT'):
                op = 'is not'
            else:
                op = 'is'
            right = self.identity(**kwargs)
            return self.binaryopnode(left, op, right, **kwargs)
        else:
            return left

    def comparison(self, **kwargs):
        return self.rightop(self.bitor, *lexer.OP_COMP, **kwargs)

    def bitor(self, **kwargs):
        return self.leftop(self.bitxor, 'OP_BITOR', **kwargs)

    def bitxor(self, **kwargs):
        return self.leftop(self.bitand, 'OP_BITXOR', **kwargs)

    def bitand(self, **kwargs):
        return self.leftop(self.shift, 'OP_BITAND', **kwargs)

    def shift(self, **kwargs):
        return self.leftop(self.addition, 'OP_LSHIFT', 'OP_RSHIFT', **kwargs)

    def addition(self, **kwargs):
        return self.leftop(self.product, 'OP_MULT', 'OP_DIV', **kwargs)

    def product(self, **kwargs):
        return self.leftop(self.modulus, 'OP_ADD', 'OP_SUB', **kwargs)

    def modulus(self, **kwargs):
        return self.leftop(self.exponent, 'OP_MOD', **kwargs)

    def exponent(self, **kwargs):
        return self.leftop(self.unary, 'OP_POW', **kwargs)

    def unary(self, **kwargs):
        if self.peek('OP_SUB', 'OP_INV', 'OP_NOT', **kwargs):
            op = self.next().value
            expr = self.unary(**kwargs)
            return self.unaryopnode(op, expr, **kwargs)
        else:
            return self.primary(**kwargs)

    def primary(self, **kwargs):
        return self._primary(self.atom(**kwargs), **kwargs)

    def _primary(self, obj, **kwargs):
        while True:
            if self.maybe('DOT'):
                attr = self.name(**kwargs)
                obj = self.lookupnode(obj, attr, **kwargs)
            elif self.maybe('LBRACKET'):
                args = self.itemlist(self.arg, 'RBRACKET', **kwargs)
                obj = self.callnode(obj, args, **kwargs)
            elif self.peek('LSQUARE'):
                subscript = self.list(**kwargs)
                obj = self.subscriptnode(obj, subscript, **kwargs)
            else:
                return obj

    def arg(self, **kwargs):
        if self.peek('OP_MULT', 'OP_POW'):
            star = self.next().value
            expr = self.expression(**kwargs)
            return self.unaryopnode(star, expr, **kwargs)
        elif self.peek('NAME'):
            name = self.name(**kwargs)
            self.next('COLON')
            expr = self.expression(**kwargs)
            return self.kwargnode(name, expr, **kwargs)
        else:
            return self.expression(**kwargs)

    def atom(self, **kwargs):
        if self.peek('LBRACE'):
            return self.brace(**kwargs)
        elif self.peek('LSQUARE'):
            return self.list(**kwargs)
        elif self.peek('LBRACKET'):
            return self.bracket(**kwargs)
        elif self.peek('NAME'):
            return self.identifier(**kwargs)
        else:
            return self.literal(**kwargs)

    def brace(self, **kwargs):
        self.next('LBRACE')
        if self.maybe('RBRACE'):
            return self.mappingnode([], **kwargs)
        else:
            expr = self.expression(**kwargs)
            if self.maybe('COLON'):
                pair = self.pairnode(expr, self.expression(**kwargs), **kwargs)
                return self.mappingnode(self._itemlist(pair, self.pair, 'RBRACE', **kwargs), **kwargs)
            else:
                return self.blocknode(self._itemlist(expr, self.expression, 'RBRACE', **kwargs), **kwargs)

    def mapping(self, **kwargs):
        self.next('LBRACE')
        return self.mappingnode(self.itemlist(self.pair, 'RBRACE', **kwargs), **kwargs)

    def pair(self, **kwargs):
        key = self.expression(**kwargs)
        self.next('COLON')
        value = self.expression(**kwargs)
        return self.pairnode(key, value, **kwargs)

    def block(self, **kwargs):
        self.next('LBRACE')
        return self.blocknode(self.itemlist(self.expression, 'RBRACE', **kwargs), **kwargs)

    def list(self, **kwargs):
        self.next('LSQUARE')
        if self.maybe('RSQUARE'):
            return self.listnode([], **kwargs)
        else:
            expr = self.expression(**kwargs)
            if self.maybe('RANGE'):
                if self.maybe('RSQUARE'):
                    return self.rangenode(expr, None, None, **kwargs)
                elif self.maybe('COMMA'):
                    step = self.unary(**kwargs)
                    return self.rangenode(expr, None, step, **kwargs)
                else:
                    stop = self.expression(**kwargs)
                    if self.maybe('RSQUARE'):
                        return self.rangenode(expr, stop, None, **kwargs)
                    elif self.maybe('COMMA'):
                        step = self.unary(**kwargs)
                        return self.rangenode(expr, stop, step, **kwargs)
                    else:
                        self.error()
            else:
                return self.listnode(self._itemlist(expr, self.expression, 'RSQUARE', **kwargs), **kwargs)

    def bracket(self, **kwargs):
        self.next('LBRACKET')
        exprs = self.itemlist(self.expression, 'RBRACKET', forcelist=False, **kwargs)
        if isinstance(exprs, list):
            return self.tuplenode(exprs, **kwargs)
        else:
            return self.groupingnode(exprs, **kwargs)

    def grouping(self, **kwargs):
        self.next('LBRACKET')
        expr = self.expression(**kwargs)
        self.next('RBRACKET')
        return self.groupingnode(expr, **kwargs)

    def tuple(self, **kwargs):
        self.next('LBRACKET')
        return self.tuplenode(self.expression, 'RBRACKET', **kwargs)

    def literal(self, **kwargs):
        if self.peek('STRING'):
            return self.string(**kwargs)
        elif self.peek('NUMBER'):
            return self.number(**kwargs)
        elif self.peek('BOOLEAN'):
            return self.boolean(**kwargs)
        elif self.peek('NONE'):
            return self.none(**kwargs)
        elif self.peek('BREAK'):
            return self.break_(**kwargs)
        elif self.peek('CONTINUE'):
            return self.continue_(**kwargs)
        elif self.peek('PASS'):
            return self.pass_(**kwargs)
        else:
            self.error()

    def string(self, **kwargs):
        return self.stringnode(self.next('STRING').value, **kwargs)

    def number(self, **kwargs):
        return self.numbernode(self.next('NUMBER').value, **kwargs)

    def boolean(self, **kwargs):
        return self.booleannode(self.next('BOOLEAN').value, **kwargs)

    def none(self, **kwargs):
        self.next('NONE')
        return self.nonenode(**kwargs)

    def break_(self, **kwargs):
        self.next('BREAK')
        return self.breaknode(**kwargs)

    def continue_(self, **kwargs):
        self.next('CONTINUE')
        return self.continuenode(**kwargs)

    def pass_(self, **kwargs):
        self.next('PASS')
        return self.passnode(**kwargs)

    def identifier(self, **kwargs):
        return self.identifiernode(self.next('NAME').value, **kwargs)

    def name(self, **kwargs):
        return self.namenode(self.next('NAME').value, **kwargs)

    # Node functions

    def assignmentnode(self, const, targets, operator, expression, **kwargs):
        return AssignmentNode(const, targets, operator, expression)

    def declarationnode(self, const, targets, **kwargs):
        return DeclarationNode(const, targets)

    def targetnode(self, const, typehint, name, **kwargs):
        return TargetNode(typehint, name)

    def typenode(self, type, params, **kwargs):
        return TypeNode(type, params)

    def ifnode(self, condition, then, default, **kwargs):
        return IfNode(condition, then, default)

    def casenode(self, value, cases, default, **kwargs):
        return CaseNode(value, cases, default)

    def trynode(self, expression, catches, **kwargs):
        return TryNode(expression, catches)

    def catchnode(self, exception, name, expression, **kwargs):
        return CatchNode(exception, name, expression)

    def fornode(self, vars, container, body, **kwargs):
        return ForNode(vars, container, body)

    def whilenode(self, condition, body, **kwargs):
        return WhileNode(condition, body)

    def iternode(self, expression, **kwargs):
        return IterNode(expression)

    def donode(self, body, **kwargs):
        return DoNode(body)

    def objectnode(self, body, **kwargs):
        return ObjectNode(body)

    def enumnode(self, flags, items, **kwargs):
        return EnumNode(flags, items)

    def modulenode(self, body, **kwargs):
        return ModuleNode(body)

    def exceptionnode(self, body, **kwargs):
        return ExceptionNode(body)

    def mutablenode(self, expression, **kwargs):
        return MutableNode(expression)

    def thrownode(self, expression, **kwargs):
        return ThrowNode(expression)

    def yieldfromnode(self, expression, **kwargs):
        return YieldFromNode(expression)

    def yieldnode(self, expression, **kwargs):
        return YieldNode(expression)

    def lambdanode(self, vparams, kwparams, returns, **kwargs):
        return LambdaNode(vparams, kwparams, returns)

    def vparamnode(self, starred, typehint, name, **kwargs):
        return VParamNode(starred, typehint, name)

    def kwparamnode(self, starred, typehint, name, default, **kwargs):
        return KwParamNode(starred, typehint, name, default)

    def binaryopnode(self, left, operator, right, **kwargs):
        return BinaryOpNode(left, operator, right)

    def unaryopnode(self, operator, operand, **kwargs):
        return UnaryOpNode(operator, operand)

    def lookupnode(self, object, attribute, **kwargs):
        return LookupNode(object, attribute)

    def callnode(self, object, vargs, kwargs, **kwargs_):
        return CallNode(object, vargs, kwargs)

    def kwargnode(self, name, value, **kwargs):
        return KwargNode(name, value)

    def subscriptnode(self, object, subscript, **kwargs):
        return SubcriptNode(object, subscript)

    def mappingnode(self, pairs, **kwargs):
        return MappingNode(pairs)

    def pairnode(self, key, value, **kwargs):
        return PairNode(key, value)

    def blocknode(self, expressions, **kwargs):
        return BlockNode(expressions)

    def listnode(self, expressions, **kwargs):
        return ListNode(expressions)

    def rangenode(self, start, stop, step, **kwargs):
        return RangeNode(start, stop, step)

    def groupingnode(self, expression, **kwargs):
        return GroupingNode(expression)

    def tuplenode(self, expressions, **kwargs):
        return TupleNode(expressions)

    def identifiernode(self, name, **kwargs):
        return IdentifierNode(name)

    def namenode(self, name, **kwargs):
        return NameNode(name)

    def stringnode(self, value, **kwargs):
        return StringNode(value)

    def numbernode(self, value, **kwargs):
        return NumberNode(value)

    def boolnode(self, value, **kwargs):
        return BoolNode(value)

    def nonenode(self, **kwargs):
        return NoneNode()

    def breaknode(self, **kwargs):
        return BreakNode()

    def continuenode(self, **kwargs):
        return ContinueNode()

    def passnode(self, **kwargs):
        return PassNode()
