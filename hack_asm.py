import argparse
import re
import os

SYMBOL_TABLE = {
    'R0':     0,
    'R1':     1,
    'R2':     2,
    'R3':     3,
    'R4':     4,
    'R5':     5,
    'R6':     6,
    'R7':     7,
    'R8':     8,
    'R9':     9,
    'R10':    10,
    'R11':    11,
    'R12':    12,
    'R13':    13,
    'R14':    14,
    'R15':    15,
    'SCREEN': 16384,
    'KBD':    24576,
    'SP':     0,
    'LCL':    1,
    'ARG':    2,
    'THIS':   3,
    'THAT':   4,
    'INS_PTR': 16
}

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

def writeFile(data, filename):
    f = open('{name}.hack'.format(name=filename.split('.')[0]), 'w')
    f.write(data)
    f.close()


def parseA(line):
    m = re.match(r'^\s*@([^\s|//*]+)', line)
    if m:
        if m.group(1).isnumeric():
            return '0{:0=15b}\n'.format(int(m.group(1)))
        elif m.group(1) in SYMBOL_TABLE:
            return '0{:0=15b}\n'.format(SYMBOL_TABLE[m.group(1)])
        else:
            SYMBOL_TABLE[m.group(1)] = SYMBOL_TABLE['INS_PTR']
            SYMBOL_TABLE['INS_PTR'] += 1
            return '0{:0=15b}\n'.format(SYMBOL_TABLE[m.group(1)])
    else:
        return 'no match for A'

def parseC(line):
    m = re.split(r'^\s*([MDA+\-=01&!|]*);?([JGELTMPNQ]{0,3})', line, maxsplit=3)
    if m:
        try:
            dest, comp = m[1].split('=')
        except (ValueError):
            comp = m[1]
            dest = ''
        jump = m[-2]
        return '111{comp}{dest}{jump}\n'.format(comp=COMP_TABLE[comp], dest=DEST_TABLE[dest], jump=JUMP_TABLE[jump])
    else:
        return 'no match for C'

def analyzeSymbols(file):
    line_count = -1
    for line in file:
        if ("@" in line or ";" in line or "=" in line) and (line[:2] != '//'):
            line_count += 1
        else:
            m = re.match(r'^\s*\((.+)\)', line)
            if m:
                SYMBOL_TABLE[m.group(1)] = line_count + 1
    file.seek(0)


def parseLine(line):
    if ("@" in line) and (line[:2] != '//'):
        return parseA(line)
    elif (";" in line or "=" in line) and (line[:2] != '//'):
        return parseC(line)
    else:
         return ''

def parse(file):
    parsed_data = ''
    analyzeSymbols(file)
    for line in file:
        parsed_data += parseLine(line)
    writeFile(parsed_data, os.path.split(file.name)[1])

def main ():
    argparser = argparse.ArgumentParser(description='Produce binary program from HACK assembly program')
    argparser.add_argument('infile', type=argparse.FileType('r', encoding='UTF-8'))
    args = argparser.parse_args()
    parse(args.infile)

if __name__ == "__main__":
    main()