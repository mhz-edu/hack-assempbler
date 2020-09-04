import argparse
import re

JUMP_TABLE = {
    '':    '000',
    'JGT': '001',
    'JEQ': '010',
    'JGE': '011',
    'JLT': '100',
    'JNE': '101',
    'JLE': '110',
    'JMP': '111'
}

DEST_TABLE = {
    '':    '000',
    'M':   '001',
    'D':   '010',
    'MD':  '011',
    'A':   '100',
    'AM':  '101',
    'AD':  '110',
    'AMD': '111'
}

COMP_TABLE = {
    '0':   '0101010',
    '1':   '0111111',
    '-1':  '0111010',
    'D':   '0001100',
    'A':   '0110000',
    '!D':  '0001101',
    '!A':  '0110001',
    '-D':  '0001111',
    '-A':  '0110011',
    'D+1': '0011111',
    'A+1': '0110111',
    'D-1': '0001110',
    'A-1': '0110010',
    'D+A': '0000010',
    'D-A': '0010011',
    'A-D': '0000111',
    'D&A': '0000000',
    'D|A': '0010101',
    'M':   '1110000',
    '!M':  '1110001',
    '-M':  '1110011',
    'M+1': '1110111',
    'M-1': '1110010',
    'D+M': '1000010',
    'D-M': '1010011',
    'M-D': '1000111',
    'D&M': '1000000',
    'D|M': '1010101'
}

def parseA(line):
    m = re.match(r'^\s*@(\d+)', line)
    if m:
        return '0{:0=15b}'.format(int(m.group(1)))
    else:
        return 'no match for A'

def parseC(line):
    m = re.split(r'^\s*([MDA+\-=01&!|]*);?([JGELTMPNQ]{0,3})', line, maxsplit=3)
    dest, comp = m[1].split('=')
    jump = m[-2]
    return '111{comp}{dest}{jump}'.format(comp=COMP_TABLE[comp], dest=DEST_TABLE[dest], jump=JUMP_TABLE[jump])


def parseLine(line):
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