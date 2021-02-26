import argparse
import re
import os
from pathlib import Path
import xml.etree.ElementTree as ET

FILE = {
    "dir": "",
    "name": ""
}

KEYWORDS = ['boolean',
            'char',
            'class',
            'constructor',
            'do',
            'else',
            'false',
            'field',
            'function',
            'if',
            'int',
            'let',
            'method',
            'null',
            'return',
            'static',
            'this',
            'true',
            'var',
            'void',
            'while']

SYMBOLS = ['{',
           '}',
           '(',
           ')',
           '[',
           ']',
           '.',
           ',',
           ';',
           '+',
           '-',
           '*',
           '/',
           '&',
           '|',
           '<',
           '>',
           '=',
           '~']

TOKEN_SEPARATOR = SYMBOLS + [' ']

PATTERNS = (
    ('|'.join(KEYWORDS), 'keyword',0),
    ('|^\\'.join(SYMBOLS), 'symbol',0),
    ('^([1-9][0-9]*$)',  'integer',1),
    ('^\"(.*)\"', 'string',1),
    ('^([a-zA-Z_][a-zA-Z_0-9]*$)', 'identifier',1)
)

# GRAMMAR = {
#     'class': {
#         'node': {
#             'token': ('keyword', 'class'),
#             'rule': addElem
#         },
#         'childList': ['className']
#     },
#     'className': {
#         'node': {
#             'token': ('identifier'),
#             'rule': addElem
#         }
#     }
# }

class tokenIterator:
    def __init__(self, input_file):
        self.input_file = input_file
        self.processed = True
        self.token = ''

    def __iter__(self):
        self.token = ''
        return self

    def getStatus(self):
        return self.processed

    def setProcessed(self):
        self.processed = True

    def getCurrentToken(self):
        return self.token

    def __next__(self):
        self.token=''
        char = self.input_file.read(1).decode('utf-8')
        # print(self.input_file.tell(), ord(char), char)
        if char in SYMBOLS:
            if char == '/':
                next_char = self.input_file.read(1).decode('utf-8')
                if next_char == '/':
                    self.input_file.readline()
                    return next(self)
                elif next_char == '*':
                    bc_end = self.input_file.read(2).decode('utf-8')
                    while(bc_end and bc_end != '*/'):
                        bc_end = self.input_file.read(2).decode('utf-8')
                    return next(self)
                else:
                    # print("not a comment")
                    self.input_file.seek(self.input_file.tell() - 1, 0)   # move read cursor one char back
                    self.token = parseToken(char)
                    self.processed = False
                    return self.token
            else:
                self.token = parseToken(char)
                self.processed = False
                return self.token
        elif char == '"':
            self.token = char
            next_char = self.input_file.read(1).decode('utf-8')
            while (next_char != '"'):
                self.token += next_char
                next_char = self.input_file.read(1).decode('utf-8')
            else:
                self.token += next_char
            self.token = parseToken(self.token)
            self.processed = False
            return self.token
        elif (char.isalnum() or char == '_'):
            while ((char != '') and not(char in TOKEN_SEPARATOR)):
                self.token += char
                char = self.input_file.read(1).decode('utf-8')
            # print('current char ', char)
            # print('current pos ', self.input_file.tell())
            self.input_file.seek(self.input_file.tell() - 1, 0)
            self.token = parseToken(self.token)
            self.processed = False
            return self.token
        elif char == '':
            raise StopIteration
        else:
            return next(self)


def parseToken(word):
    rules = [ matchApplyBuilder(pattern, token_type, match_group) for (pattern, token_type, match_group) in PATTERNS ]
    token_matched = False
    for matchRule, applyRule in rules:
        if matchRule(word) and not(token_matched):
            token_matched = True
            return applyRule(word)
    return None

def matchApplyBuilder(pattern, token_type, match_group):
    def matchRule(word):
        return re.search(pattern, word)
    def applyRule(word):
        match = re.search(pattern, word)
        if match:
            return (token_type, match.group(match_group))
    return (matchRule, applyRule)


def compile(tokenizer):
    def compileToken(expected_type=None, expected_text=None, token=None, allow_to_fail=False):
        if token == None:
            if tokenizer.getStatus():
                token_type, token_text = next(tokenizer)
                print('Retrieved next token: ', token_type, token_text)
            else:
                token_type, token_text = tokenizer.getCurrentToken()
                print('Using existing token: ', token_type, token_text)
        else:
            token_type, token_text = token
            print('Using passed token: ', token_type, token_text)
        if (expected_type == None):
            elem = ET.Element(token_type)
            elem.text = token_text
            tokenizer.setProcessed()
            return elem
        elif (token_type == expected_type):
            if (expected_text == None):
                elem = ET.Element(token_type)
                elem.text = token_text
                tokenizer.setProcessed()
                return elem
            elif (expected_text == token_text):
                elem = ET.Element(token_type)
                elem.text = token_text
                tokenizer.setProcessed()
                return elem
            elif (token_text in expected_text):
                elem = ET.Element(token_type)
                elem.text = token_text
                tokenizer.setProcessed()
                return elem
            else:
                if allow_to_fail:
                    return ET.Element('')
                else:
                    raise ValueError('expected text ', expected_text,  ' got ', token_text)
        elif (token_type in expected_type):
            elem = ET.Element(token_type)
            elem.text = token_text
            tokenizer.setProcessed()
            return elem
        else:
            if allow_to_fail:
                return ET.Element('')
            else:
                raise ValueError('expected type ', expected_type, ' got ', token_type )

    def compileTokenList(stop, delim, tokens, include_stop=True):
        result = []
        stop_type, stop_text = stop
        delim_type, delim_text = delim
        for func in tokens:
            elem = func()
            result.append(elem)
        elem = compileToken(expected_type=stop_type, expected_text=stop_text, allow_to_fail=True)
        if elem.tag == '':
            while ((elem.tag != stop_type) or (elem.text != stop_text)) :
                elem = compileToken(expected_type=delim_type, expected_text=delim_text)
                result.append(elem)
                for func in tokens:
                    elem = func()
                    result.append(elem)
                elem = compileToken(expected_type=stop_type, expected_text=stop_text, allow_to_fail=True)
            print('stop element found')
            if include_stop:
                print('stop elemt included')
                result.append(elem)
            return result
        else:
            if include_stop:
                print('stop elemt included')
                result.append(elem)
            return result

    def compileTokenListSeq(tokens):
        result = []
        while True:
            try:
                temp_result = []
                for func in tokens:
                    elem = func()
                    try:
                        temp_result.extend(elem)
                        print('processed as list')
                    except TypeError:
                        temp_result.append(elem)
                        print('processed as single')
                    temp_result += elem
                result += temp_result
            except ValueError:
                print('value error is raised')
                return result
        return result

    def compileClass():
        root = ET.Element('class')
        child_list = [compileToken(expected_type='keyword', expected_text='class'),
                    compileToken(expected_type='identifier'),
                    compileToken(expected_type='symbol', expected_text='{'),
                    compileClassVarDec(),
                    compileSubroutineDecAlt(),
                    compileToken(expected_type='symbol', expected_text='}')]
        for child in child_list:
            if child != None:
                root.append(child)
        return ET.tostring(root, encoding='unicode', method='xml')
 

    def compileClassVarDec():
        def compileClassVarKwd():
            return compileToken(expected_type='keyword', expected_text=['static', 'field'])

        def compileVars():
            return compileTokenList(('symbol',';'), ('symbol',','), [compileVarName])
        
        child_list = compileTokenListSeq([compileClassVarKwd,
                                          compileType,
                                          compileVars])
        if child_list != []:
            root = ET.Element('classVarDec')
            for child in child_list:
                root.append(child)
            return root
        else:
            return None

    def compileVarName():
        return compileToken('identifier', None)

    

    def compileType(void=False):
        text_list = ['int', 'char', 'boolean']
        if void:
            text_list.append('void')
        elem = compileToken(expected_type=['keyword', 'identifier'], expected_text=text_list)
        return elem
        
    def compileSubroutineDec():
        root = ET.Element('subroutineDec')
        child_list = [compileToken(expected_type='keyword', expected_text=['constructor', 'function', 'method']),
                      compileType(void=True),
                      compileToken(expected_type='identifier'),
                      compileParameterList(),
                      compileSubBody()]
        for child in child_list:
            root.append(child)
        return root
    def compileSubroutineDecAlt():
        
        def compileSubDecKwd():
            return compileToken(expected_type='keyword', expected_text=['constructor', 'function', 'method'])
        
        def compileSubType():
            return compileType(void=True)

        def compileSubName():
            return compileToken(expected_type='identifier')

        def compileLPar():
            return compileToken(expected_type='symbol', expected_text='(')
        
        def compileRPar():
            return compileToken(expected_type='symbol', expected_text=')')

        def compileParameterList():
            root = ET.Element('parameterList')
            child_list = compileTokenList(('symbol',')'), ('symbol',','), [compileType, compileVarName], include_stop=False)
            print(child_list)
            for child in child_list:
                root.append(child)
            return root
        
        child_list = compileTokenListSeq([compileSubDecKwd,
                                         compileSubType,
                                         compileSubName,
                                         compileLPar,
                                         compileParameterList,
                                         compileRPar])
        if child_list != []:
            root = ET.Element('subroutineDec')
            for child in child_list:
                root.append(child)
            return root
        else:
            return None

    

    def compileSubBody():
        root = ET.Element('subroutineBody')
        child_list = [compileToken(expected_type='symbol', expected_text='{'),
                    compileVarDec(),
                    compileStatements(),
                    compileToken(expected_type='symbol', expected_text='}')]
        for child in child_list:
            root.append(child)
        return root

    def compileVarDec():
        root = ET.Element('varDec')
        # child_list = [compileToken(expected_type='keyword', expected_text='var'),
        #               compileType()] + compileTokenList(',', ('symbol',';'), 'identifier')
        for child in child_list:
            root.append(child)
        return root

    def compileStatements():
        root = ET.Element('statements')
        return root

    return compileClass()

def writeFile(data, filename):
    f = open('{name}.asm'.format(name=filename), 'w')
    f.write(data)
    f.close()



def parse(path):
    p = Path(path)
    FILE['name'] = p.stem
    print('Opening single file %s' % FILE['name'])
    parsed_data = ''
    with open(p, mode='rb') as f:
        tokenizer = tokenIterator(f)
        print(compile(tokenizer))
            # print(compile(tokenIterator(f)))
    #print(parsed_data)
    # writeFile(parsed_data, FILE['name'])

def parsedir(path):
    p = Path(path)
    FILE['dir'] = p.name
    parsed_data = ''
    FILE['name'] = 'Sys'
    for f in p.glob('*.vm'):
        FILE['name'] = f.stem
        print('Opening dir file %s' % FILE['name'])
        for line in f.open():
            parsed_data += parseLine(line)
    # writeFile(parsed_data, FILE['dir'])        

def main ():
    argparser = argparse.ArgumentParser(description='Produce xml from JACK program')
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