#!/usr/bin/python3

import base64
import copy
import uritemplate
import urllib.parse
import urllib.request
import json
import os.path

conf_files = [os.path.relpath ('config.json')]
default_config = {
    'connection_method' : 'https',
    'api_host'          : 'api.github.com',
    'api_root'          : '/',
    'archive_format'    : 'tarball',
    'authentication'    : None
}
config = None

default_cache = {
    'api_root'     : None,
    'auth_headers' : {
        id(None) : {}
    }
}
cache = None

def load_configuration ():
    global config
    config = copy.deepcopy (default_config)
    global cache
    cache = copy.deepcopy (default_cache)
    for filename in conf_files:
        try:
            with open (filename, 'r') as file:
                config.update (json.load (file))
        except FileNotFoundError:
            pass


def api_root ():
    if (cache ['api_root'] == None):
        cache ['api_root'] = api_get (api_url ())
    return cache ['api_root']

def auth_headers (auth):
    if (id(auth) not in cache ['auth_headers']):
        if (auth ['type'] == 'basic'):
            username = auth ['username']
            password = auth ['password']
            raw      = '{}:{}'.format (username, password)
            # TODO: Is UTF-8 right?
            raw64    = base64.standard_b64encode (bytes (raw, 'utf-8'))
            ascii64  = str (raw64, 'ascii')
            headers  = {'Authorization' : 'Basic {}'.format (ascii64)}
            cache ['auth_headers'][id(auth)] = headers
        else:
            raise
    return cache ['auth_headers'][id(auth)]


def api_url (*path):
    method  = config ['connection_method']
    host    = config ['api_host']
    root    = config ['api_root']
    base    = urllib.parse.urlunsplit ((method, host, root, '', ''))
    relpath = '/'.join (map (lambda s: urllib.parse.quote (s, safe=''), path))
    url     = urllib.parse.urljoin (base, relpath)
    return url

def api_get (url):
    # TODO: Error checking
    headers  = auth_headers (config ['authentication'])
    request  = urllib.request.Request (url, headers=headers)
    response = urllib.request.urlopen (request)
    raw_data = response.read ()
    return json.loads (raw_data.decode ('utf-8'))

def get_repo (owner, repo_name):
    url = uritemplate.expand (api_root () ['repository_url'], {
        'owner' : owner,
        'repo'  : repo_name
    })
    return api_get (url)

def save_archive (repo, directory=None, filename=None, archive_format=None, ref=None):
    if (archive_format == None):
        archive_format = config ['archive_format']
    if (directory == None):
        directory = os.curdir
    if (filename == None):
        extensions = {
            'tarball' : 'tar.gz',
            'zipball' : 'zip'
        }
        filename = '{}.{}'.format (repo ['name'], extensions [archive_format])

    path = os.path.join (directory, filename)
    with open (path, 'wb') as file:
        url = uritemplate.expand (repo ['archive_url'], {
            'archive_format' : archive_format,
            'ref'            : ref
        })
        response = urllib.request.urlopen (url)
        # TODO: May fail for large files?
        file.write (response.read ())


import argparse

def main ():
    arg_parser = argparse.ArgumentParser ()
    arg_parser.add_argument ('command', help='one of "get"')
    arg_parser.add_argument ('owner', help='owner of "repo"')
    arg_parser.add_argument ('repo', help='repo owned by "owner"')
    arg_parser.add_argument ('--archive-type', help='one of "tarball", "zipball"')
    arg_parser.add_argument ('--save-dir', help='directory in which to save repos')
    args = arg_parser.parse_args ()

    if (args.command == 'get'):
        load_configuration ()
        repo = get_repo (args.owner, args.repo)
        save_archive (repo, directory=args.save_dir, archive_format=args.archive_type)
    else:
        raise

if __name__ == '__main__':
    main ()
else:
    load_configuration ()
