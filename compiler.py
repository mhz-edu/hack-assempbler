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
    ('|'.join(['^{}$'.format(x) for x in KEYWORDS]), 'keyword',0),
    ('|^\\'.join(SYMBOLS), 'symbol',0),
    ('^([0-9]*$)',  'integerConstant',1),
    ('^\"(.*)\"', 'stringConstant',1),
    ('^([a-zA-Z_][a-zA-Z_0-9]*$)', 'identifier',1)
)
CLASS_ST = []
SUB_ST = []
CLASS_INDEX = {'field':  0,
               'static': 0}
SUB_INDEX = {'argument': 0,
             'local':    0}
CUR_ID = {}

CLASS_NAME =''

OPS = {'+':'add',
       '-':'sub',
       '*':'call Math.multiply',
       '/':'call Math.divide',
       '&':'and',
       '|':'or',
       '<':'lt',
       '>':'gt',
       '=':'eq'}

UNOPS = {'-':'neg', '~':'neg'}

def varDefined(var_name):
    sub_vars = [x['name'] for x in SUB_ST]
    class_vars = [x['name'] for x in CLASS_ST]
    if var_name in sub_vars:
        return SUB_ST[sub_vars.index(var_name)]
    elif var_name in class_vars:
        return CLASS_ST[class_vars.index(var_name)]
    else:
        return None


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

    def createXmlElement(token, attributes={}):
        token_type, token_text = token
        elem = ET.Element(token_type)
        elem.text = '{}'.format(token_text)
        elem.attrib = attributes
        return elem
        

    def compileToken(expected_type, expected_text=None, allow_to_fail=False, tokenizer=tokenizer, attributes={}):
        if tokenizer.getStatus():
            token_type, token_text = next(tokenizer)
            # print('Retrieved next token: ', token_type, token_text)
        else:
            token_type, token_text = tokenizer.getCurrentToken()
            # print('Using existing token: ', token_type, token_text)
        if (expected_text == None):
            if (expected_type == token_type):
                elem = createXmlElement((token_type, token_text), attributes)
                tokenizer.setProcessed()
                return elem
            else:
                if allow_to_fail:
                    return None
                else:
                    raise ValueError('Expeting type "{}", got type "{}"'.format(expected_type, token_type))    
        else:
            if (expected_text == token_text) and (expected_type == token_type):
                elem = createXmlElement((token_type, token_text),attributes)
                tokenizer.setProcessed()
                return elem
            else:
                if allow_to_fail:
                    return None
                else:
                    raise ValueError('Expeting {}, got {}'.format(expected_text, token_text))
    
    def compileTokenAlt(expected_type, expected_text=None, code=str, allow_to_fail=False):
        if tokenizer.getStatus():
            token_type, token_text = next(tokenizer)
            # print('Retrieved next token: ', token_type, token_text)
        else:
            token_type, token_text = tokenizer.getCurrentToken()
            # print('Using existing token: ', token_type, token_text)
        if (expected_text == None):
            if (expected_type == token_type):
                elem = createXmlElement((token_type, code(token_text)), {})
                tokenizer.setProcessed()
                return elem
            else:
                if allow_to_fail:
                    return None
                else:
                    raise ValueError('Expeting type "{}", got type "{}"'.format(expected_type, token_type))    
        else:
            if (expected_text == token_text) and (expected_type == token_type):
                elem = createXmlElement((token_type, code(token_text)),{})
                tokenizer.setProcessed()
                return elem
            else:
                if allow_to_fail:
                    return None
                else:
                    raise ValueError('Expeting {}, got {}'.format(expected_text, token_text))

    def compileOrAlt(fns, store_in_st=''):
        for fn, arg in fns:
            elem = fn(*arg, allow_to_fail=True)
            if elem != None:
                if store_in_st == '':
                    return elem
                else:
                    CUR_ID[store_in_st] = elem.text
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
        child_list.append(compileClassName())
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

    def compileClassName():
        atr = {'category':'class', 'used':'False'}
        elem = compileToken(expected_type='identifier', attributes=atr)
        CLASS_NAME = elem.text
        return elem
 

    def compileClassVarDec():
        def compileClassVarField():
            global CUR_ID
            CUR_ID = {}
            CUR_ID['category'] = 'field'
            return compileToken('keyword','field')
            
        def compileClassVarStatic():
            global CUR_ID
            CUR_ID = {}
            CUR_ID['category'] = 'static'
            return compileToken('keyword','static')

        def compileVarNameGr(atr):
            def formGroup1():
                return compileGroup([
                    (compileToken, ['symbol', ',']),
                    (compileVarName, [atr, False, True])
                ])
            return compileZeroOrMore(formGroup1)

        def formClassVarField():
            atr = {'category':'field', 'used':'False'}
            return compileGroup([
                (compileClassVarField, []),
                (compileType, []),
                (compileVarName, [atr, False, True]),
                (compileVarNameGr, [atr]),
                (compileToken, ['symbol', ';'])
            ])
        
        def formClassVarStatic():
            atr = {'category':'static', 'used':'False'}
            return compileGroup([
                (compileClassVarStatic, []),
                (compileType, []),
                (compileVarName, [atr, False, True]),
                (compileVarNameGr, [atr]),
                (compileToken, ['symbol', ';'])
            ])

        def formClassVarDec():
            stmnts = [formClassVarField, formClassVarStatic]
            for fn in stmnts:
                try:
                    elem = fn()
                    if elem != None:
                        return elem
                except ValueError:
                    continue
            raise ValueError('Cannot parse')

        child_list = formClassVarDec()
        if child_list != []:
            root = ET.Element('classVarDec')
            for child in child_list:
                root.append(child)
            return root
        else:
            return []

    def compileVarName(atr={}, allow_to_fail=False, store=False):
        global CUR_ID
        CUR_ID['name'] = ''
        CUR_ID['index'] = ''
        elem = compileToken('identifier', None, allow_to_fail=allow_to_fail)
        if store:
            # index = len(list(filter(lambda x: x['category']==CUR_ID['category'], CLASS_ST)))
            index = CLASS_INDEX[CUR_ID['category']]
            CUR_ID['name'] = elem.text
            CUR_ID['index'] = str(index)
            CLASS_INDEX[CUR_ID['category']] += 1
            elem.attrib = CUR_ID.copy()
            CLASS_ST.append(CUR_ID.copy())
            print(CUR_ID)
            
            return elem
        else:
            return elem


    def compileType():
        return compileOrAlt([
            (compileToken, ['keyword','int']),
            (compileToken, ['keyword','char']),
            (compileToken, ['keyword','boolean']),
            (compileVarName, [])
        ], 'type')
        
    def compileSubroutineDec():
        global SUB_INDEX, SUB_ST
        SUB_ST = [{'category': 'argument', 'type': CLASS_NAME, 'name': 'this', 'index': '0'}]
        SUB_INDEX = {'argument': 1, 'local':    0}
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

        def compileParamName(atr={}, allow_to_fail=False, store=False):
            global CUR_ID
            CUR_ID['name'] = ''
            CUR_ID['index'] = ''
            elem = compileToken('identifier', None, allow_to_fail=allow_to_fail)
            if store:
                index = SUB_INDEX[CUR_ID['category']]
                CUR_ID['name'] = elem.text
                CUR_ID['index'] = str(index)
                SUB_INDEX[CUR_ID['category']] += 1
                elem.attrib = CUR_ID.copy()
                SUB_ST.append(CUR_ID.copy())
                print(CUR_ID)
                
                return elem
            else:
                return elem

        def compileParamList():
            global CUR_ID
            CUR_ID['category'] = 'argument'
            def formGroup1():
                return compileGroup([
                    (compileType, []),
                    (compileParamName, [{}, False, True])
                ])

            def formGroup2():
                return compileGroup([
                    (compileToken, ['symbol', ',']),
                    (compileType, []),
                    (compileParamName, [{}, False, True])
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
            global CUR_ID
            CUR_ID['category'] = 'local'
            def compileVarNameGr():
                def formGroup1():
                    return compileGroup([
                        (compileToken, ['symbol', ',']),
                        (compileLocalVarName, [{}, False, True])
                    ])
                return compileZeroOrMore(formGroup1)


            def formGroup():
                return compileGroup([
                    (compileToken, ['keyword', 'var']),
                    (compileType, []),
                    (compileLocalVarName, [{}, False, True]),
                    (compileVarNameGr, []),
                    (compileToken, ['symbol',';'])
                ])

            def compileLocalVarName(atr={}, allow_to_fail=False, store=False):
                global CUR_ID
                CUR_ID['name'] = ''
                CUR_ID['index'] = ''
                elem = compileToken('identifier', None, allow_to_fail=allow_to_fail)
                if store:
                    index = SUB_INDEX[CUR_ID['category']]
                    CUR_ID['name'] = elem.text
                    CUR_ID['index'] = str(index)
                    SUB_INDEX[CUR_ID['category']] += 1
                    elem.attrib = CUR_ID.copy()
                    SUB_ST.append(CUR_ID.copy())
                    print(CUR_ID)
                    
                    return elem
                else:
                    return elem

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
                    (writeS, [compileStatements]),
                    (compileToken, ['symbol', '}'])
                ])

        def writeS(fn):
            statements = fn()
            return writeStatements(statements)

        def writeStatements(statements):
            result = ET.Element('code')
            result.extend([writeSt(x) for x in statements])
            return result

        def writeSt(elem):
            result = ET.Element('code')
            if elem.tag == 'letStatement':
                result.append(elem.find('code'))
                let_ident_code = ET.Element('code')
                let_ident = elem.find('identifier')

                if let_ident.get('category') == 'field' or let_ident.get('category') == 'static':
                    var_segment = 'this'
                else:
                    var_segment = let_ident.get('category')
                let_ident_code.text = 'pop {} {}'.format(var_segment, let_ident.get('index'))
                result.append(let_ident_code)
                return result
            elif elem.tag == 'doStatement':
                result.append(writeSubCall(elem))
                return result
            else:
                return elem


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
                    (writeExpr, [compileExpression]),
                    (compileToken, ['symbol', ']'])
                ])

            def compileSubExpr():
                elem = compileZeroOrOne(formGroup1)
                if elem != None:
                    return elem
                else:
                    return []
            
            def compileLetVarName():
                elem = compileToken('identifier', None)
                var = varDefined(elem.text)
                if var != None:
                    elem.attrib = var
                    elem.attrib['used'] = 'True'
                    return elem
                else:
                    raise SyntaxError('{} variable is not defined'.format(elem.text))


            def formGroup2():
                return compileGroup([
                    (compileToken, ['keyword', 'let']),
                    (compileLetVarName, []),
                    (compileSubExpr, []),
                    (compileToken, ['symbol', '=']),
                    (writeE, [compileExpression]),
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
            def compileDoVarName():
                elem = compileToken('identifier', None)
                var = varDefined(elem.text)
                if var != None:
                    elem.attrib = var
                    elem.attrib['used'] = 'True'
                    return elem
                else:
                    return elem

            def formGroup2():
                return compileGroup([
                    (compileToken, ['keyword', 'do']),
                    (compileDoVarName, []),
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
                    return writeExpr(elem)
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


    def writeE(fn):
        expr = fn()
        return writeExpr(expr)
            

    def writeExpr(elem):

        def writeOp(elem, table):
            result = ET.Element('code')
            result.text = table[elem.text]
            return result

        def writeTermList(elem):
            result = ET.Element('code')
            if len(elem) > 1:
                result.extend([writeTerm(elem[0]),
                                writeTermList(elem[2:]),
                                writeOp(elem[1], OPS)])
            else:
                result.extend([writeTerm(elem[0])])
            return result

        def writeTerm(elem):
            result = ET.Element('code')
            if len(elem) == 1:
                if elem[0].tag == 'integerConstant':
                    result.text = 'push constant {}'.format(elem[0].text)
                   
                elif elem[0].tag == 'identifier':
                    if elem[0].get('category') == 'field' or elem[0].get('category') == 'static':
                        var_segment = 'this'
                    else:
                        var_segment = elem[0].get('category')
                    result.text = 'push {} {}'.format(var_segment, elem[0].get('index'))
                   
                elif elem[0].tag == 'keyword':
                    mapping = {'null': 'constant 0', 'true': 'constant -1', 'false': 'constant 0', 'this': '???'}
                    result.text = 'push {}'.format(mapping[elem[0].text])
                return result
            elif len(elem) == 2:
                result.extend([writeTerm(elem[1]),
                               writeOp(elem[0], UNOPS)])
                return result
            elif len(elem) == 3:
                result.extend([writeExpr(elem[1])])
                return result
        ET.dump(elem)
        if len(elem) == 1:
            return writeTerm(elem[0])
        else:
            return writeTermList(elem)


        

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

            def compileExpVarName():
                elem = compileToken('identifier', None)
                var = varDefined(elem.text)
                if var != None:
                    elem.attrib = var
                    elem.attrib['used'] = 'True'
                    return elem
                else:
                    raise SyntaxError('{} variable is not defined'.format(elem.text))

        
            result = [compileExpVarName()]
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
        
    
    def writeSubCall(elem_list):
        result = ET.Element('code')
        idents = []
        exprs = []
        for item in elem_list:
            if item.tag == 'identifier':
                idents.append(item.text)
            elif item.tag == 'expressionList':
                exprs.extend(item)
        
        if exprs != []:
            result.extend([writeExpr(x) for x in exprs])
        call = ET.Element('code')
        call.text = 'call {}'.format('.'.join(idents))
        result.append(call)
        return result


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
    f = open('{name}.xml'.format(name=filename), 'w')
    f.write(data)
    f.close()



def parse(path):
    p = Path(path)
    FILE['name'] = p.stem
    print('Opening single file %s' % FILE['name'])
    parsed_data = ''
    with open(p, mode='rb') as f:
        tokenizer = tokenIterator(f)
        parsed_data = compile(tokenizer)
    # print(parsed_data)
    writeFile(parsed_data, FILE['name'])

def parsedir(path):
    p = Path(path)
    FILE['dir'] = p.name
    parsed_data = ''
    FILE['name'] = 'Sys'
    for fl in p.glob('*.jack'):
        FILE['name'] = fl.stem
        print('Opening dir file %s' % FILE['name'])
        with open(fl, mode='rb') as f:
            tokenizer = tokenIterator(f)
            parsed_data = compile(tokenizer)
        writeFile(parsed_data, FILE['name'])    

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