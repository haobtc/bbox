import os, sys
import uuid
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
parser.add_argument(
    '--prefix',
    type=str,
    default='',
    help='cluster prefix, a cluster of boxes share the prefix')

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
        'etcd': ['127.0.0.1:2379'],
        'prefix': args.prefix or uuid.uuid4().hex,
        'language': lang,
        'port_range': [30000, 40000],
        'bind_ip': '127.0.0.1'
        }
    config_file = os.path.join(prjdir, 'tup.config.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, indent=2, sort_keys=True)

if __name__ == '__main__':
    main()
