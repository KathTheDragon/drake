from dataclasses import dataclass, field, InitVar

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
    numerator: int
    denominator: int = field(default=1)
    imaginary: bool = field(default=False)

    def __post_init__(self):
        if self.denominator < 0:
            self.numerator *= -1
            self.denominator *= -1
        gcd = math.gcd(self.numerator, self.denominator)
        if gcd != 1:
            self.numerator //= gcd
            self.denominator //= gcd

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
                return Number(numerator*10**exponent, 1, bool(imagunit))
            else:
                return Number(numerator, 10**(-exponent), bool(imagunit))

@dataclass
class Boolean:
    value: bool

    @staticmethod
    def parse(boolean):
        return Boolean(boolean=='true')
