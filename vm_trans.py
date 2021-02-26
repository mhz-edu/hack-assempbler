import argparse
import re
import os
from pathlib import Path

BOOT = {
    "code": "@256\nD=A\n@SP\nM=D\n"
}

TR_TABLE = {
    "add" : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=D+M\nM=D\nD=A+1\n@SP\nM=D\n",
    "sub" : "@SP\nM=M-1\nA=M\nD=M\nA=A-1\nD=M-D\nM=D\nD=A+1\n@SP\nM=D\n",
    "neg" : "@SP\nA=M\nA=A-1\nM=-M\n",
    "eq"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=M-D\n@TRUE.{num}\nD;JEQ\n@SP\nA=M\nA=A-1\nA=A-1\nM=0\n@END.{num}\n0;JMP\n(TRUE.{num})\n@SP\nA=M\nA=A-1\nA=A-1\nM=-1\n(END.{num})\n@SP\nM=M-1\n",
    "gt"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=M-D\n@TRUE.{num}\nD;JGT\n@SP\nA=M\nA=A-1\nA=A-1\nM=0\n@END.{num}\n0;JMP\n(TRUE.{num})\n@SP\nA=M\nA=A-1\nA=A-1\nM=-1\n(END.{num})\n@SP\nM=M-1\n",
    "lt"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=M-D\n@TRUE.{num}\nD;JLT\n@SP\nA=M\nA=A-1\nA=A-1\nM=0\n@END.{num}\n0;JMP\n(TRUE.{num})\n@SP\nA=M\nA=A-1\nA=A-1\nM=-1\n(END.{num})\n@SP\nM=M-1\n",
    "and" : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=D&M\nM=D\nD=A+1\n@SP\nM=D\n",
    "or"  : "@SP\nA=M\nA=A-1\nD=M\nA=A-1\nD=D|M\nM=D\nD=A+1\n@SP\nM=D\n",
    "not" : "@SP\nA=M\nA=A-1\nM=!M\n"
}

SEG_PTRS = {
    "local" : "LCL",
    "argument": "ARG",
    "this": "THIS",
    "that": "THAT",
    "LABEL_COUNT": 0
}

FLOW_TABLE = {
    "label": "({funcName}${label})\n",
    "goto": "@{funcName}${label}\n0;JMP\n",
    "if-goto": "@SP\nM=M-1\nA=M\nD=M\n@{funcName}${label}\nD;JNE\n"
}

FUNC_TABLE = {
    "function": "({caller})\n{push0n}",
    "call":  '''//push retAddrLabel
                @{caller}$ret.{i}\nD=A\n@SP\nA=M\nM=D\n@SP\nM=M+1
                //push LCL
                @LCL\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1
                //push ARG
                @ARG\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1
                //push THIS
                @THIS\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1
                //push THAT
                @THAT\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1
                //reposition ARG
                @SP\nD=M\n@5\nD=D-A\n@{nVars}\nD=D-A\n@ARG\nM=D
                //reposition LCL
                @SP\nD=M\n@LCL\nM=D
                //goto {calee}
                @{calee}\n0;JMP\n
                ({caller}$ret.{i})\n''',
    "return":    '''//endframe
                    @LCL\nD=M\n@endframe\nM=D
                    //get retAddr
                    @endframe
                    D=M\n@5\nD=D-A\nA=D\nD=M\n@{caller}$ret.{i}\nM=D
                    //reposition return val for the caller
                    @SP\nM=M-1\nA=M\nD=M\n@ARG\nA=M\nM=D
                    //reposition SP for the caller
                    @ARG\nD=M\n@SP\nM=D+1
                    //restore THAT
                    @endframe\nM=M-1\nA=M\nD=M\n@THAT\nM=D
                    //restore THIS
                    @endframe\nM=M-1\nA=M\nD=M\n@THIS\nM=D
                    //restore ARG
                    @endframe\nM=M-1\nA=M\nD=M\n@ARG\nM=D
                    //restore LCL
                    @endframe\nM=M-1\nA=M\nD=M\n@LCL\nM=D
                    //goto retAddr
                    @{caller}$ret.{i}\nA=M\n0;JMP\n''',
    "caller": "",
    "calee": "",
    "calee_count": 0
}

FILE = {
    "dir": "",
    "name": ""
}

def writeFile(data, filename):
    f = open('{name}.asm'.format(name=filename), 'w')
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
    elif args[0] == 'push' and args[1] == 'temp':
        res = '@5\nD=A\n@{value}\nD=D+A\nA=D\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'.format(value=args[2])
    elif  args[0] == 'pop' and args[1] == 'temp':
        res = '@5\nD=A\n@{value}\nD=D+A\n@SP\nA=M\nM=D\nA=A-1\nD=M\nA=A+1\nA=M\nM=D\n@SP\nM=M-1\n'.format(value=args[2])
    elif args[0] == 'push' and args[1] == 'static':
        res = '@{varname}.{value}\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'.format(varname=FILE['name'], value=args[2])
    elif args[0] == 'pop' and args[1] == 'static':
        res = '@SP\nM=M-1\nA=M\nD=M\n@{varname}.{value}\nM=D\n'.format(varname=FILE['name'], value=args[2])
    elif args[0] == 'push' and args[1] == 'pointer':
        res = '@{ptr}\nD=M\n@SP\nA=M\nM=D\n@SP\nM=M+1\n'.format(ptr='THIS' if args[2]=='0' else 'THAT')
    elif args[0] == 'pop' and args[1] == 'pointer':
        res = '@SP\nM=M-1\nA=M\nD=M\n@{ptr}\nM=D\n'.format(ptr='THIS' if args[2]=='0' else 'THAT')
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
        elif command[0] in FLOW_TABLE:
            res = '//{com}\n'.format(com=command[0]) + FLOW_TABLE[command[0]].format(filename=FILE['name'],
                                                                                     funcName=FUNC_TABLE['caller'],
                                                                                     label=command[1])
            return res
        elif command[0] in FUNC_TABLE:
            if command[0] == 'function':
                FUNC_TABLE['caller'] = command[1]
                res = '//{com}\n'.format(com=command[0]) + FUNC_TABLE[command[0]].format(filename=FILE['name'],
                                                                                         caller=FUNC_TABLE['caller'],
                                                                                         nVars=command[2],
                                                                                         push0n=('@SP\nA=M\nM=0\n@SP\nM=M+1\n'*int(command[2])))
            elif command[0] == 'call':
                FUNC_TABLE['calee'] = command[1]
                FUNC_TABLE['calee_count'] += 1
                res = '//{com}\n'.format(com=command[0]) + FUNC_TABLE[command[0]].format(filename=FILE['name'],
                                                                                         caller=FUNC_TABLE['caller'],
                                                                                         calee=FUNC_TABLE['calee'],
                                                                                         i = FUNC_TABLE['calee_count'],
                                                                                         nVars=command[2],
                                                                                         push0n=('@SP\nA=M\nM=0\n@SP\nM=M+1\n'*int(command[2])))

            else:
                res = '//{com}\n'.format(com=command[0]) + FUNC_TABLE[command[0]].format(filename=FILE['name'],
                                                                                         caller=FUNC_TABLE['caller'],
                                                                                         i = FUNC_TABLE['calee_count'])
                FUNC_TABLE['calee'] = ''
                FUNC_TABLE['calee_count'] -= 1
            return res
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

def parse(path):
    p = Path(path)
    FILE['name'] = p.stem
    print('Opening single file %s' % FILE['name'])
    parsed_data = ''
    # Add bootstrap code
    FUNC_TABLE['caller'] = 'Bootstrap'
    parsed_data += BOOT['code']
    parsed_data += parseCommand('call Sys.init 0')
    for line in p.open():
        parsed_data += parseLine(line)
    #print(parsed_data)
    writeFile(parsed_data, FILE['name'])

def parsedir(path):
    p = Path(path)
    FILE['dir'] = p.name
    parsed_data = ''
    # Add bootstrap code
    FILE['name'] = 'Sys'
    FUNC_TABLE['caller'] = 'Bootstrap'
    parsed_data += BOOT['code']
    parsed_data += parseCommand('call Sys.init 0')
    for f in p.glob('*.vm'):
        FILE['name'] = f.stem
        print('Opening dir file %s' % FILE['name'])
        for line in f.open():
            parsed_data += parseLine(line)
    writeFile(parsed_data, FILE['dir'])
        

def main ():
    argparser = argparse.ArgumentParser(description='Produce HACK assembly program from VM code')
    argparser.add_argument('input')
    args = argparser.parse_args()
    if os.path.isfile(args.input):
        parse(args.input)
    elif os.path.isdir(args.input):
        parsedir(args.input)
    else:
        print('Path error')
        return None

if __name__ == "__main__":
    main()