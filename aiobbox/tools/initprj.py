import os, sys
import uuid
import json
import argparse

parser = argparse.ArgumentParser(
    prog='bbox init',
    description='init a bbox project')
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

    bbox_dir = os.path.join(os.getcwd(), '.bbox')
    config_file = os.path.join(bbox_dir, 'ticket.json')
    gitignore_file = os.path.join(os.getcwd(), '.gitignore')

    if os.path.exists(config_file):
        print('project already initialized!',
              file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(bbox_dir):
        os.makedirs(bbox_dir)

    prjname = os.path.basename(os.getcwd())

    lang = args.language
    if lang not in ('python3', 'python'):
        print('language {} not supported'.format(lang),
              file=sys.stderr)
        sys.exit(1)

    if lang == 'python':
        lang = 'python3'

    config_json = {
        'name': prjname,
        'etcd': ['127.0.0.1:2379'],
        'prefix': args.prefix or uuid.uuid4().hex,
        'language': lang,
        'bind_ip': '127.0.0.1'
        }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_json, f, indent=2, sort_keys=True)

    if not os.path.exists(gitignore_file):
        lines = [
            '*.pyc',
            'node_modules/',
            '.DS_Store',
            'certs/',
            'tmp/',
            'bbox.ticket.json'
        ]
        with open(gitignore_file, 'w', encoding='utf-8') as f:
            f.write(''.join(line + '\n' for line in lines))

if __name__ == '__main__':
    main()
