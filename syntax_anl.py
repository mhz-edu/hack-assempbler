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

TOKEN_SEPARATOR = SYMBOLS + [' ', '\r']

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

    def createXmlElement(token):
        token_type, token_text = token
        elem = ET.Element(token_type)
        elem.text = token_text
        return elem
        

    def compileToken(expected_type, expected_text=None, allow_to_fail=False, tokenizer=tokenizer):
        if tokenizer.getStatus():
            token_type, token_text = next(tokenizer)
            print('Retrieved next token: ', token_type, token_text)
        else:
            token_type, token_text = tokenizer.getCurrentToken()
            print('Using existing token: ', token_type, token_text)
        if (expected_text == None):
            if (expected_type == token_type):
                elem = createXmlElement((token_type, token_text))
                tokenizer.setProcessed()
                return elem
            else:
                if allow_to_fail:
                    return None
                else:
                    raise ValueError('Expeting type "{}", got type "{}"'.format(expected_type, token_type))    
        else:
            if (expected_text == token_text) and (expected_type == token_type):
                elem = createXmlElement((token_type, token_text))
                tokenizer.setProcessed()
                return elem
            else:
                if allow_to_fail:
                    return None
                else:
                    raise ValueError('Expeting {}, got {}'.format(expected_text, token_text))


    def compileOrAlt(fns):
        for fn, arg in fns:
            elem = fn(*arg, allow_to_fail=True)
            if elem != None:
                return elem
        raise ValueError('Unexpected token')

    def compileGroup(fns):
        result = []
        for fn, arg in fns:
            elem = fn(*arg)
            try:
                elem.tag
                result.append(elem)
            except AttributeError:
                result.extend(elem)
        return result

    def compileZeroOrOne(fn):
        try:
            elem = fn()
            return elem
        except ValueError:
            return None

    def compileZeroOrMore(fn):
        result = []
        while True:
            try:
                elem = fn()
                try:
                    result.extend(elem)
                except TypeError:
                    result.append(elem)
            except ValueError:
                break
        return result

    def compileKwd():
        return compileGroup([
            (compileOrAlt, [[
                [compileToken, ['keyword', 'field']],
                [compileToken, ['keyword', 'static']]
            ]]),
            (compileToken, ['keyword', 'int']),
            (compileToken, ['identifier', None]),
        ])

    def compileGrp1():
        return compileGroup([
            (compileType, []),
            (compileToken, ['identifier', None])
        ])
    def compileGrp2():
        return compileGroup([
            (compileToken, ['symbol', ',']),
            (compileType, []),
            (compileToken, ['identifier', None])
        ])
    def compileGrp3():
        return compileGroup([
            (compileGrp1, []),
            (compileZeroOrMore, [compileGrp2])
        ])

    def compileGrp4():
        return compileZeroOrOne(compileGrp3)

    def compileClass():
        root = ET.Element('class')
        child_list = []
        child_list.append(compileToken(expected_type='keyword', expected_text='class'))
        child_list.append(compileToken(expected_type='identifier'))
        child_list.append(compileToken(expected_type='symbol', expected_text='{'))
        elem = compileClassVarDec()
        if elem != []:
            child_list.append(elem)
        elem = compileSubroutineDec()
        if elem != []:
            child_list.append(elem)
        child_list.append(compileToken(expected_type='symbol', expected_text='}'))
        for child in child_list:
            if child != None:
                root.append(child)
        return ET.tostring(root, encoding='unicode', method='xml')
 

    def compileClassVarDec():
        def compileClassVarKwd():
            return compileOrAlt([
                (compileToken, ['keyword','static']),
                (compileToken, ['keyword','field'])
            ])

        def compileVarNameGr():
            def formGroup1():
                return compileGroup([
                    (compileToken, ['symbol', ',']),
                    (compileToken, ['identifier', None])
                ])
            return compileZeroOrMore(formGroup1)

        def formClassVarGr():
            def formGroup2():
                return compileGroup([
                    (compileClassVarKwd, []),
                    (compileType, []),
                    (compileToken, ['identifier', None]),
                    (compileVarNameGr, []),
                    (compileToken, ['symbol', ';'])
                ])
            return compileZeroOrMore(formGroup2)

        child_list = formClassVarGr()
        if child_list != []:
            root = ET.Element('classVarDec')
            for child in child_list:
                root.append(child)
            return root
        else:
            return []

    def compileVarName():
        return compileToken('identifier', None)


    def compileType():
        return compileOrAlt([
            (compileToken, ['keyword','int']),
            (compileToken, ['keyword','char']),
            (compileToken, ['keyword','boolean'])
        ])
        
    def compileSubroutineDec():
        def compileSubDecKwd():
            return compileOrAlt([
                (compileToken, ['keyword','constructor']),
                (compileToken, ['keyword','function']),
                (compileToken, ['keyword','method'])
            ])

        def compileTypeVoid():
            return compileOrAlt([
                (compileToken, ['keyword','int']),
                (compileToken, ['keyword','char']),
                (compileToken, ['keyword','boolean']),
                (compileToken, ['keyword','void'])
            ])

        def compileParamList():
            def formGroup1():
                return compileGroup([
                    (compileType, []),
                    (compileToken, ['identifier', None])
                ])

            def formGroup2():
                return compileGroup([
                    (compileToken, ['symbol', ',']),
                    (compileType, []),
                    (compileToken, ['identifier', None])
                ])
            def formGroup3():
                return compileGroup([
                    (formGroup1, []),
                    (compileZeroOrMore, [formGroup2])
                ])
            def formGroup4():
               return compileZeroOrOne(formGroup3)

            child_list = formGroup4()
            root = ET.Element('parameterList')
            if child_list != None:
                for child in child_list:
                    root.append(child)
                return root
            else:
                root.text = '\r\n'
                return root
            

        def formSubGr():
            def formGroup2():
                return compileGroup([
                    (compileSubDecKwd, []),
                    (compileTypeVoid, []),
                    (compileToken, ['identifier', None]),
                    (compileToken, ['symbol', '(']),
                    (compileParamList, []),
                    (compileToken, ['symbol', ')']),
                    (compileSubBody, [])
                ])
            return compileZeroOrMore(formGroup2)
            
        child_list = formSubGr()
        if child_list != []:
            root = ET.Element('subroutineDec')
            for child in child_list:
                root.append(child)
            return root
        else:
            return []

    def compileSubBody():
        def compileVarDec():
            def compileVarNameGr():
                def formGroup1():
                    return compileGroup([
                        (compileToken, ['symbol', ',']),
                        (compileToken, ['identifier', None])
                    ])
                return compileZeroOrMore(formGroup1)


            def formGroup():
                return compileGroup([
                    (compileToken, ['keyword', 'var']),
                    (compileType, []),
                    (compileToken, ['identifier', None]),
                    (compileVarNameGr, []),
                    (compileToken, ['symbol',';'])
                ])

            child_list = compileZeroOrMore(formGroup)
            root = ET.Element('varDec')
            if child_list != []:
                for child in child_list:
                    root.append(child)
                return root
            else:
                root.text = '\r\n'
                return root

        def formBodyGr():
            return compileGroup([
                    (compileToken, ['symbol', '{']),
                    (compileVarDec, []),
                    (compileStatements, []),
                    (compileToken, ['symbol', '}'])
                ])

        child_list = formBodyGr()
        root = ET.Element('subroutineBody')
        if child_list != []:
            for child in child_list:
                root.append(child)
            return root
        else:
            root.text = '\r\n'
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