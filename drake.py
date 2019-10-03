import argparse
from drake.lexer import lex
from drake.parser import Parser

parser = argparse.ArgumentParser(description='Compile or interpret a Drake program.')
parser.add_argument('cmd', choices=['build', 'run'])
parser.add_argument('file')
parser.add_argument('-o', '--output', action='store', dest='output', type=str)

args = parser.parse_args()

try:
    with open(args.file) as f:
        input_file = f.read()

    ast = Parser(lex(input_file)).ast

    if args.output:
        with open(args.output, 'w+') as f:
            [f.write(node.pprint()) for node in ast]
    else:
        [print(node.pprint()) for node in ast]

except FileNotFoundError:
    print(f'Could not find `{args.file}`')