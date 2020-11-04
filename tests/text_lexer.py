import pytest
from drake.src import lexer

class TestLex:
    @pytest.mark.xfail(reason='lexer doesn\'t reset column counter at newlines')
    def test_blanks(self):
        blanks = lexer.lex('''
        pass // line comment
        pass /* block comment
        block comment 2 */ pass      pass

        ''')
        assert list(blanks) == [
            lexer.Token('NEWLINE', 'nl', 1, 0),
            lexer.Token('PASS', 'pass', 2, 8),
            lexer.Token('NEWLINE', 'nl', 2, 12),
            lexer.Token('PASS', 'pass', 3, 8),
            lexer.Token('NEWLINE', 'nl', 3, 12),
            lexer.Token('PASS', 'pass', 4, 27),
            lexer.Token('PASS', 'pass', 4, 37),
            lexer.Token('NEWLINE', 'nl', 4, 41),
            lexer.Token('EOF', 'eof', 6, 8)
        ]

    def test_delimiters(self):
        delimiters = lexer.lex('-> .. . , : ( ) [ ] { }')
        assert list(delimiters) == [
            lexer.Token('LAMBDA', '->', 1, 0),
            lexer.Token('RANGE', '..', 1, 3),
            lexer.Token('DOT', '.', 1, 6),
            lexer.Token('COMMA', ',', 1, 8),
            lexer.Token('COLON', ':', 1, 10),
            lexer.Token('LBRACKET', '(', 1, 12),
            lexer.Token('RBRACKET', ')', 1, 14),
            lexer.Token('LSQUARE', '[', 1, 16),
            lexer.Token('RSQUARE', ']', 1, 18),
            lexer.Token('LBRACE', '{', 1, 20),
            lexer.Token('RBRACE', '}', 1, 22),
            lexer.Token('EOF', 'eof', 1, 23)
        ]

    def test_assignments(self):
        assignments = lexer.lex('+= -= **= *= /= %= &= ^= |= <<= >>= =')
        assert list(assignments) == [
            lexer.Token('OP_ADDEQ', '+=', 1, 0),
            lexer.Token('OP_SUBEQ', '-=', 1, 3),
            lexer.Token('OP_POWEQ', '**=', 1, 6),
            lexer.Token('OP_MULTEQ', '*=', 1, 10),
            lexer.Token('OP_DIVEQ', '/=', 1, 13),
            lexer.Token('OP_MODEQ', '%=', 1, 16),
            lexer.Token('OP_BITANDEQ', '&=', 1, 19),
            lexer.Token('OP_BITXOREQ', '^=', 1, 22),
            lexer.Token('OP_BITOREQ', '|=', 1, 25),
            lexer.Token('OP_LSHIFTEQ', '<<=', 1, 28),
            lexer.Token('OP_RSHIFTEQ', '>>=', 1, 32),
            lexer.Token('OP_ASSIGN', '=', 1, 36),
            lexer.Token('EOF', 'eof', 1, 37)
        ]

    def test_comparisons(self):
        comparisons = lexer.lex('<= < >= > != ==')
        assert list(comparisons) == [
            lexer.Token('OP_LE', '<=', 1, 0),
            lexer.Token('OP_LT', '<', 1, 3),
            lexer.Token('OP_GE', '>=', 1, 5),
            lexer.Token('OP_GT', '>', 1, 8),
            lexer.Token('OP_NE', '!=', 1, 10),
            lexer.Token('OP_EQ', '==', 1, 13),
            lexer.Token('EOF', 'eof', 1, 15)
        ]

    def test_operators(self):
        operators = lexer.lex('+ - ** * / % & ^ | << >> ! and xor or not is in')
        assert list(operators) == [
            lexer.Token('OP_ADD', '+', 1, 0),
            lexer.Token('OP_SUB', '-', 1, 2),
            lexer.Token('OP_POW', '**', 1, 4),
            lexer.Token('OP_MULT', '*', 1, 7),
            lexer.Token('OP_DIV', '/', 1, 9),
            lexer.Token('OP_MOD', '%', 1, 11),
            lexer.Token('OP_BITAND', '&', 1, 13),
            lexer.Token('OP_BITXOR', '^', 1, 15),
            lexer.Token('OP_BITOR', '|', 1, 17),
            lexer.Token('OP_LSHIFT', '<<', 1, 19),
            lexer.Token('OP_RSHIFT', '>>', 1, 22),
            lexer.Token('OP_INV', '!', 1, 25),
            lexer.Token('OP_AND', 'and', 1, 27),
            lexer.Token('OP_XOR', 'xor', 1, 31),
            lexer.Token('OP_OR', 'or', 1, 35),
            lexer.Token('OP_NOT', 'not', 1, 38),
            lexer.Token('OP_IS', 'is', 1, 42),
            lexer.Token('OP_IN', 'in', 1, 45),
            lexer.Token('EOF', 'eof', 1, 47)
        ]

    def test_keywords(self):
        keywords = lexer.lex('as case catch const do else enum exception flags for if iter let module mutable object raises then throw try while')
        assert list(keywords) == [
            lexer.Token('KW_AS', 'as', 1, 0),
            lexer.Token('KW_CASE', 'case', 1, 3),
            lexer.Token('KW_CATCH', 'catch', 1, 8),
            lexer.Token('KW_CONST', 'const', 1, 14),
            lexer.Token('KW_DO', 'do', 1, 20),
            lexer.Token('KW_ELSE', 'else', 1, 23),
            lexer.Token('KW_ENUM', 'enum', 1, 28),
            lexer.Token('KW_EXCEPTION', 'exception', 1, 33),
            lexer.Token('KW_FLAGS', 'flags', 1, 43),
            lexer.Token('KW_FOR', 'for', 1, 49),
            lexer.Token('KW_IF', 'if', 1, 58),
            lexer.Token('KW_ITER', 'iter', 1, 61),
            lexer.Token('KW_LET', 'let', 1, 66),
            lexer.Token('KW_MODULE', 'module', 1, 70),
            lexer.Token('KW_MUTABLE', 'mutable', 1, 77),
            lexer.Token('KW_OBJECT', 'object', 1, 85),
            lexer.Token('KW_RAISES', 'raises', 1, 92),
            lexer.Token('KW_THEN', 'then', 1, 99),
            lexer.Token('KW_THROW', 'throw', 1, 104),
            lexer.Token('KW_TRY', 'try', 1, 110),
            lexer.Token('KW_WHILE', 'while', 1, 114),
            lexer.Token('EOF', 'eof', 1, 125)
        ]

    def test_booleans(self):
        booleans = lexer.lex('true false')
        assert list(booleans) == [
            lexer.Token('BOOLEAN', 'true', 1, 0),
            lexer.Token('BOOLEAN', 'false', 1, 5),
            lexer.Token('EOF', 'eof', 1, 10)
        ]

    def test_singletons(self):
        singletons = lexer.lex('none break continue pass')
        assert list(singletons) == [
            lexer.Token('NONE', 'none', 1, 0),
            lexer.Token('BREAK', 'break', 1, 5),
            lexer.Token('CONTINUE', 'continue', 1, 11),
            lexer.Token('PASS', 'pass', 1, 20),
            lexer.Token('EOF', 'eof', 1, 24)
        ]

    def test_strings(self):
        strings = lexer.lex('\'abc\\de"\' "abc\'"')
        assert list(strings) == [
            lexer.Token('STRING', '\'abc\\de"\'', 1, 0),
            lexer.Token('STRING', '"abc\'"', 1, 10),
            lexer.Token('EOF', 'eof', 1, 16)
        ]

    def test_numbers(self):
        numbers = lexer.lex('0b_0_1 0o_0_1234567 0x_0_123456789abcdefABCDEF 0_123456789.0123456789e0123456789j 0e+1 0e-1 0E1J')
        assert list(numbers) == [
            lexer.Token('NUMBER', '0b_0_1', 1, 0),
            lexer.Token('NUMBER', '0o_0_1234567', 1, 7),
            lexer.Token('NUMBER', '0x_0_123456789abcdefABCDEF', 1, 20),
            lexer.Token('NUMBER', '0_123456789.0123456789e0123456789j', 1, 47),
            lexer.Token('NUMBER', '0e+1', 1, 82),
            lexer.Token('NUMBER', '0e-1', 1, 87),
            lexer.Token('NUMBER', '0E1J', 1, 92),
            lexer.Token('EOF', 'eof', 1, 96)
        ]

    def test_identifiers(self):
        identifiers = lexer.lex('a_bC _a! _?')
        assert list(identifiers) == [
            lexer.Token('IDENTIFIER', 'a_bC', 1, 0),
            lexer.Token('IDENTIFIER', '_a!', 1, 5),
            lexer.Token('IDENTIFIER', '_?', 1, 9),
            lexer.Token('EOF', 'eof', 1, 11)
        ]

    def test_unknowns(self):
        unknowns = lexer.lex('£$€;@#~?')
        assert list(unknowns) == [
            lexer.Token('UNKNOWN', '£', 1, 0),
            lexer.Token('UNKNOWN', '$', 1, 1),
            lexer.Token('UNKNOWN', '€', 1, 2),
            lexer.Token('UNKNOWN', ';', 1, 3),
            lexer.Token('UNKNOWN', '@', 1, 4),
            lexer.Token('UNKNOWN', '#', 1, 5),
            lexer.Token('UNKNOWN', '~', 1, 6),
            lexer.Token('UNKNOWN', '?', 1, 7),
            lexer.Token('EOF', 'eof', 1, 8)
        ]
