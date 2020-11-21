from dataclasses import dataclass, field, InitVar
import math, re

@dataclass
class Registry:
    values: list = field(default_factory=list)

    def register(self, value):
        if item in self.values:
            index = self.values.index(item)
        else:
            index = len(self.values)
            self.values.append(item)
        return index

## Singletons
@dataclass
class None_:
    pass

@dataclass
class Break:
    pass

@dataclass
class Continue:
    pass

## Literals
@dataclass
class String:
    value: str

    @staticmethod
    def parse(string):
        string = string[1:-1]  # Also needs escape and interpolation processing
        return String(string)

@dataclass
class Number:
    numerator: tuple[int, int]
    denominator: int

    def __init__(self, numerator, denominator=1):
        if isinstance(numerator, int):
            real, imag = numerator, 0
        else:
            real, imag = numerator
        if isinstance(denominator, int):
            dreal, dimag = denominator, 0
        else:
            dreal, dimag = denominator
        if dimag == 0:
            if dreal < 0:
                real *= -1
                imag *= -1
                denominator = -dreal
            else:
                denominator = dreal
        else:
            real = real*dreal + imag*dimag
            imag = imag*dreal - real*dimag
            denominator = dreal**2 + dimag**2
        gcd = math.gcd(real, imag, denominator)
        if gcd != 1:
            real //= gcd
            imag //= gcd
            denominator //= gcd
        self.numerator = real, imag
        self.denominator = denominator

    @staticmethod
    def parse(number):
        number = number.replace('_', '')
        if number.startswith('0b'):
            return Number(int(number, 2))
        elif number.startswith('0o'):
            return Number(int(number, 8))
        elif number.startswith('0x'):
            return Number(int(number, 16))
        else:
            match = re.match(r'(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?([jJ])?', number)
            integer, fractional, exponent, imagunit = match.groups(default='')
            exponent = int(exponent or '0')
            if fractional:
                exponent -= len(fractional)
                integer += fractional
            numerator = integer.lstrip('0')
            if exponent >= 0:
                numerator *= 10**exponent
                denominator = 1
            else:
                denominator = 10**(-exponent)
            if imagunit:
                numerator = (0, numerator)
            return Number(numerator, denominator)

@dataclass
class Boolean:
    value: bool

    @staticmethod
    def parse(boolean):
        return Boolean(boolean=='true')
