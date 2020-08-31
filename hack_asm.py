import argparse
import re

def parseA(line):
    m = re.match(r'^\s*@(\d+)', line)
    if m:
        return '0{:0=15b}'.format(int(m.group(1)))
    else:
        return 'no match for A'

def parseC(line):
    m = re.split(r'^\s*([MDA+\-=01&!|]*);?([JGELTMPNQ]{0,3})', line, maxsplit=3)
    return m[1:-1]


def parseLine(line):
    print(line)
    if line[0] == '@':
        return parseA(line)
    elif line[0] in ['M', 'D', 'A'] or line[0].isnumeric():
        return parseC(line)
    else:
         return 'not a command'

def parse(file):
    print('Source file parsing will be there')
    for line in file:
        print(parseLine(line))

def main ():
    argparser = argparse.ArgumentParser(description='Produce binary program from HACK assembly program')
    argparser.add_argument('infile', type=argparse.FileType('r', encoding='UTF-8'))
    args = argparser.parse_args()
    parse(args.infile)

if __name__ == "__main__":
    main()