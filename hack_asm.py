import argparse

def parse(file):
    print('Source file parsing will be there')

def main ():
    argparser = argparse.ArgumentParser(description='Produce binary program from HACK assembly program')
    argparser.add_argument('infile', type=argparse.FileType('r', encoding='UTF-8'))
    args = argparser.parse_args()
    parse(args.infile)

if __name__ == "__main__":
    main()