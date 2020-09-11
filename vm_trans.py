import argparse
import re
import os



TR_TABLE = {
    "add" : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=D+M\nM=D\nD=A+1\n@SP\nM=D\n",
    "sub" : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=D-M\nM=D\nD=A+1\n@SP\nM=D\n",
    "neg" : "@SP\nA=M\nA=A-1\nM=-M\n",
    "eq"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=M-D\n@TRUE.{num}\nD;JEQ\n@SP\nA=M\nA=A-1\nA=A-1\nM=0\n@END.{num}\n0;JMP\n(TRUE.{num})\n@SP\nA=M\nA=A-1\nA=A-1\nM=1\n(END.{num})\n@SP\nM=M-1\n",
    "gt"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=M-D\n@TRUE.{num}\nD;JGT\n@SP\nA=M\nA=A-1\nA=A-1\nM=0\n@END.{num}\n0;JMP\n(TRUE.{num})\n@SP\nA=M\nA=A-1\nA=A-1\nM=1\n(END.{num})\n@SP\nM=M-1\n",
    "lt"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=M-D\n@TRUE.{num}\nD;JLT\n@SP\nA=M\nA=A-1\nA=A-1\nM=0\n@END.{num}\n0;JMP\n(TRUE.{num})\n@SP\nA=M\nA=A-1\nA=A-1\nM=1\n(END.{num})\n@SP\nM=M-1\n",
    "and" : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=D&M\nM=D\nD=A+1\n@SP\nM=D\n",
    "or"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=D|M\nM=D\nD=A+1\n@SP\nM=D\n",
    "not" : "@SP\nA=M\nA=A-1\nM=!M\n"
}

SEG_PTRS = {
    "local" : "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT",
    "temp": 5,
    "LABEL_COUNT": 0
}

FILENAME = ''

def writeFile(data, filename):
    f = open('{name}.asm'.format(name=filename.split('.')[0]), 'w')
    f.write(data)
    f.close()

def pushPop(args):
    #print('start parsing push/pop')
    #print(args)
    if args[:-1] == ['push', 'constant']:
        res = '@{value}\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'.format(value=args[2])
    elif args[0] == 'push' and args[1] in SEG_PTRS:
        res = '@{segment}\nD=M\n@{value}\nD=D+A\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'.format(segment=SEG_PTRS[args[1]], value=args[2])
    elif  args[0] == 'pop' and args[1] in SEG_PTRS:
        res = '@{segment}\nD=M\n@{value}\nD=D+A\n@SP\nA=M\nM=D\nA=A-1\nD=M\nA=A+1\nA=M\nM=D\n@SP\nM=M-1\n'.format(segment=SEG_PTRS[args[1]], value=args[2])
    elif args[0] == 'push' and args[1] == 'static':
        res = '@{varname}.{value}\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'.format(varname=FILENAME, value=args[2])
    elif args[0] == 'pop' and args[1] == 'static':
        res = '@SP\nM=M-1\nA=M\nD=M\n@{varname}.{value}\nM=D\n'.format(varname=FILENAME, value=args[2])
    elif args[0] == 'push' and args[1] == 'pointer':
        res = '@{ptr}\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'.format(ptr='THIS' if args[2]==0 else 'THAT')
    elif args[0] == 'pop' and args[1] == 'pointer':
        res = '@SP\nM=M-1\nA=M\nD=M\n@{ptr}\nM=D\n'.format(ptr='THIS' if args[2]==0 else 'THAT')
    else:
        res = 'cannot parse the command'
    res = '//{command}\n'.format(command=' '.join(args)) + res
    return res


def parseCommand(line):
    res = ''
    m = re.match(r'^\s*([^//*]+)', line)
    if m:
        command = m.group(1).rstrip().split()
        if command[0] in TR_TABLE:
            if command[0] in ['eq', 'gt', 'lt']:
                res = '//{com}\n'.format(com=command[0]) + TR_TABLE[command[0]].format(num=SEG_PTRS['LABEL_COUNT'])
                SEG_PTRS['LABEL_COUNT'] += 1
                return res
            else:
                return '//{com}\n'.format(com=command[0]) + TR_TABLE[command[0]]
        elif len(command) == 3:
            return pushPop(command)
        else:
            return 'unknown command\n'
    


def parseLine(line):
    #print('parsing line')
    if line.isspace() or (line[:2] == '//'):
        #print('not a command')
        return ''
    else:
        #print('command found')
        return parseCommand(line)

def parse(file):
    FILENAME = os.path.split(file.name)[1].split('.')[0]
    parsed_data = ''
    for line in file:
        parsed_data += parseLine(line)
    #print(parsed_data)
    writeFile(parsed_data, os.path.split(file.name)[1])

def main ():
    argparser = argparse.ArgumentParser(description='Produce HACK assembly program from VM code')
    argparser.add_argument('infile', type=argparse.FileType('r', encoding='UTF-8'))
    args = argparser.parse_args()
    parse(args.infile)

if __name__ == "__main__":
    main()