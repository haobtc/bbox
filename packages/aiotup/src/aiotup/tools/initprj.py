import os, sys
import json
import argparse

parser = argparse.ArgumentParser(
    description='init a tup project')
parser.add_argument(
    'dir',
    type=str,
    help='the directory to init')
parser.add_argument(
    '--language',
    type=str,
    default='python3',
    help='the language, default is python3')

def main():
    args = parser.parse_args()
    prjdir = args.dir
    if os.path.exists(prjdir):
        print('project directory already exist!',
              file=sys.stderr)
        sys.exit(1)
        
    os.makedirs(prjdir)

    lang = args.language
    if lang not in ('python3', 'python'):
        print('language {} not supported'.format(lang),
              file=sys.stderr)
        sys.exit(1)

    if lang == 'python':
        lang = 'python3'
        
    config_json = {
        'name': prjdir,
        'etcd': ['localhost:2379'],
        'language': lang
        }
    config_file = os.path.join(prjdir, 'tup.config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, indent=4, sort_keys=True)

if __name__ == '__main__':
    main()
