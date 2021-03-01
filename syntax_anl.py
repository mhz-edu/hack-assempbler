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
    ('^([1-9][0-9]*$)',  'integerConstant',1),
    ('^\"(.*)\"', 'stringConstant',1),
    ('^([a-zA-Z_][a-zA-Z_0-9]*$)', 'identifier',1)
)

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
                    blockcomment_end1 = self.input_file.read(1).decode('utf-8')
                    blockcomment_end2 = self.input_file.read(1).decode('utf-8')
                    while not(blockcomment_end1 == '*' and blockcomment_end2 == '/') and not(blockcomment_end1 == '' or blockcomment_end2 == ''):
                        blockcomment_end1 = self.input_file.read(1).decode('utf-8')
                        if blockcomment_end1 == '*':
                            blockcomment_end2 = self.input_file.read(1).decode('utf-8')
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
            # print('Retrieved next token: ', token_type, token_text)
        else:
            token_type, token_text = tokenizer.getCurrentToken()
            # print('Using existing token: ', token_type, token_text)
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
                    elem.tag
                    result.append(elem)
                except AttributeError:
                    result.extend(elem)
            except ValueError:
                break
        return result

    def compileClass():
        root = ET.Element('class')
        child_list = []
        child_list.append(compileToken(expected_type='keyword', expected_text='class'))
        child_list.append(compileToken(expected_type='identifier'))
        child_list.append(compileToken(expected_type='symbol', expected_text='{'))
        elem = compileZeroOrMore(compileClassVarDec)
        if elem != []:
            child_list.extend(elem)
        elem = compileZeroOrMore(compileSubroutineDec)
        if elem != []:
            child_list.extend(elem)
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
            return compileGroup([
                (compileClassVarKwd, []),
                (compileType, []),
                (compileToken, ['identifier', None]),
                (compileVarNameGr, []),
                (compileToken, ['symbol', ';'])
            ])

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
            (compileToken, ['keyword','boolean']),
            (compileToken, ['identifier', None])
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
                (compileToken, ['identifier', None]),
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
            return compileGroup([
                (compileSubDecKwd, []),
                (compileTypeVoid, []),
                (compileToken, ['identifier', None]),
                (compileToken, ['symbol', '(']),
                (compileParamList, []),
                (compileToken, ['symbol', ')']),
                (compileSubBody, [])
            ])
            
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

            def compileVarDecLine():
                child_list = formGroup()
                root = ET.Element('varDec')
                if child_list != []:
                    for child in child_list:
                        root.append(child)
                    return root
                else:
                    root.text = '\r\n'
                    return root    

            return compileZeroOrMore(compileVarDecLine)
            

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
        def compileStatement():
            stmnts = [compileLet, compileIf, compileWhile, compileDo, compileReturn]
            for fn in stmnts:
                try:
                    elem = fn()
                    if elem != None:
                        return elem
                except ValueError:
                    continue
            raise ValueError('Cannot parse')

        def compileLet():
            def formGroup1():
                return compileGroup([
                    (compileToken, ['symbol', '[']),
                    (compileExpression, []),
                    (compileToken, ['symbol', ']'])
                ])

            def compileSubExpr():
                elem = compileZeroOrOne(formGroup1)
                if elem != None:
                    return elem
                else:
                    return []

            def formGroup2():
                return compileGroup([
                    (compileToken, ['keyword', 'let']),
                    (compileToken, ['identifier', None]),
                    (compileSubExpr, []),
                    (compileToken, ['symbol', '=']),
                    (compileExpression, []),
                    (compileToken, ['symbol', ';'])
                ])
            child_list = formGroup2()

            if child_list != []:
                root = ET.Element('letStatement')
                for child in child_list:
                    root.append(child)
                return root
            else:
                return []

        def compileIf():

            def formElseGroup():
                return compileGroup([
                    (compileToken, ['keyword', 'else']),
                    (compileToken, ['symbol', '{']),
                    (compileStatements, []),
                    (compileToken, ['symbol', '}'])
                ])

            def compileElseExpr():
                elem = compileZeroOrOne(formElseGroup)
                if elem != None:
                    return elem
                else:
                    return []
            
            def formGroup2():
                return compileGroup([
                    (compileToken, ['keyword', 'if']),
                    (compileToken, ['symbol', '(']),
                    (compileExpression, []),
                    (compileToken, ['symbol', ')']),
                    (compileToken, ['symbol', '{']),
                    (compileStatements, []),
                    (compileToken, ['symbol', '}']),
                    (compileElseExpr, [])
                ])

            child_list = formGroup2()

            if child_list != []:
                root = ET.Element('ifStatement')
                for child in child_list:
                    root.append(child)
                return root
            else:
                return []


        def compileWhile():
            def formGroup2():
                return compileGroup([
                    (compileToken, ['keyword', 'while']),
                    (compileToken, ['symbol', '(']),
                    (compileExpression, []),
                    (compileToken, ['symbol', ')']),
                    (compileToken, ['symbol', '{']),
                    (compileStatements, []),
                    (compileToken, ['symbol', '}'])
                ])

            child_list = formGroup2()

            if child_list != []:
                root = ET.Element('whileStatement')
                for child in child_list:
                    root.append(child)
                return root
            else:
                return []

        def compileDo():
            def formGroup2():
                return compileGroup([
                    (compileToken, ['keyword', 'do']),
                    (compileToken, ['identifier', None]),
                    (compileSubCall, []),
                    (compileToken, ['symbol', ';'])
                ])

            child_list = formGroup2()
            if child_list != []:
                root = ET.Element('doStatement')
                for child in child_list:
                    root.append(child)
                return root
            else:
                return []

        def compileReturn():
            def compileRetExpr():
                elem = compileZeroOrOne(compileExpression)
                if elem != None:
                    return elem
                else:
                    return []

            def formGroup2():
                return compileGroup([
                    (compileToken, ['keyword', 'return']),
                    (compileRetExpr, []),
                    (compileToken, ['symbol', ';'])
                ])

            child_list = formGroup2()

            if child_list != []:
                root = ET.Element('returnStatement')
                for child in child_list:
                    root.append(child)
                return root
            else:
                return []

        child_list = compileZeroOrMore(compileStatement)
        root = ET.Element('statements')
        if child_list != []:
            for child in child_list:
                root.append(child)
            return root
        else:
            root.text = '\r\n'
            return root

    def compileExpression():
        def formTerm():
            terms = [compileIntConst, compileStrConst, compileKwdConst, formParGr, formUnaryGr,formIdentCase]
            for fn in terms:
                try:
                    elem = fn()
                    if elem != None:
                        return elem
                except ValueError:
                    continue
            raise ValueError('Cannot parse')

        def compileTerm():
            root = ET.Element('term')
            elem = formTerm()
            try:
                elem.tag
                root.append(elem)
            except AttributeError:
                root.extend(elem)
            return root

        def compileIntConst():
            return compileToken('integerConstant', None)

        def compileStrConst():
            return compileToken('stringConstant', None)


        def compileKwdConst():
            return compileOrAlt([
                (compileToken, ['keyword','true']),
                (compileToken, ['keyword','false']),
                (compileToken, ['keyword','null']),
                (compileToken, ['keyword','this'])
            ])
        
        def compileOp():
            return compileOrAlt([
                (compileToken, ['symbol','+']),
                (compileToken, ['symbol','-']),
                (compileToken, ['symbol','*']),
                (compileToken, ['symbol','/']),
                (compileToken, ['symbol','&']),
                (compileToken, ['symbol','|']),
                (compileToken, ['symbol','<']),
                (compileToken, ['symbol','>']),
                (compileToken, ['symbol','='])
            ])

        def compileUnaryOp():
            return compileOrAlt([
                (compileToken, ['symbol','~']),
                (compileToken, ['symbol','-'])
            ])


        
        
        
        
        def formTermsGr():
            def formGroup1():
                return compileGroup([
                    (compileOp, []),
                    (compileTerm, [])
                ])

            return compileGroup([
                (compileTerm, []),
                (compileZeroOrMore, [formGroup1])
            ])

        def formParGr():
            return compileGroup([
                (compileToken, ['symbol','(']),
                (compileExpression, []),
                (compileToken, ['symbol',')']),
            ])

        def formUnaryGr():
            return compileGroup([
                (compileUnaryOp, []),
                (compileTerm, [])
            ])

        def formIdentCase():
            def formGroup1():
                return compileGroup([
                    (compileToken, ['symbol','[']),
                    (compileExpression, []),
                    (compileToken, ['symbol',']'])
                ])

            # return formGroup3()
            result = [compileToken('identifier', None)]
            cases = [formGroup1, compileSubCall]
            for fn in cases:
                try:
                    elem = fn()
                    if elem != []:
                        result.extend(elem)
                        return result
                except ValueError:
                    continue
            return result

        child_list = formTermsGr()

        if child_list != []:
            root = ET.Element('expression')
            for child in child_list:
                root.append(child)
            return root
        else:
            return []
    
    
    def compileExprList():
            def formGroup1():
                return compileGroup([
                    (compileToken, ['symbol', ',']),
                    (compileExpression, [])
                ])
            def formGroup2():
                return compileGroup([
                    (compileExpression, []),
                    (compileZeroOrMore, [formGroup1])
                ])
            def formGroup3():
               return compileZeroOrOne(formGroup2)
            
            child_list = formGroup3()
            root = ET.Element('expressionList')
            if child_list != None:
                for child in child_list:
                    root.append(child)
                return root
            else:
                root.text = '\r\n'
                return root
        
    


    def compileSubCall():
        def formGroup1():
            return compileGroup([
                (compileToken, ['symbol', '.']),
                (compileToken, ['identifier', None]),
                (compileToken, ['symbol','(']),
                (compileExprList, []),
                (compileToken, ['symbol',')']),
            ])
        
        def formGroup2():
                return compileGroup([
                    (compileToken, ['symbol', '(']),
                    (compileExprList, []),
                    (compileToken, ['symbol',')']),
                ])
        
        cases = [formGroup1, formGroup2]
        for fn in cases:
            try:
                elem = fn()
                if elem != []:
                    return elem
            except ValueError:
                continue
        raise ValueError('Cannot parse')

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