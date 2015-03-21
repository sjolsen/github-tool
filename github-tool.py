#!/usr/bin/python3

import uritemplate
import urllib.parse
import urllib.request
import json
import os.path

conf_files = ['/etc/github-tool.json',
              os.path.expanduser ('~/.config/github-tool/config.json')]
configuration = {
    'connection_method' : 'https',
    'api_host'          : 'api.github.com',
    'api_root'          : '/',
    'archive_format'    : 'tarball'
}

def load_configuration ():
    for filename in conf_files:
        try:
            with open (filename, 'r') as file:
                configuration.update (json.load (file))
        except FileNotFoundError:
            pass
    return configuration
load_configuration ()


def api_get (url):
    # TODO: Error checking
    response = urllib.request.urlopen (url)
    raw_data = response.read ()
    return json.loads (raw_data.decode ('utf-8'))

def api_root ():
    method = configuration ['connection_method']
    host   = configuration ['api_host']
    root   = configuration ['api_root']
    url    = urllib.parse.urlunsplit ((method, host, root, '', ''))
    return api_get (url)

def get_repo (api, owner, repo_name):
    url = uritemplate.expand (api ['repository_url'], {
        'owner' : owner,
        'repo'  : repo_name
    })
    return api_get (url)

def save_archive (repo, directory=None, filename=None, archive_format=None, ref=None):
    if (archive_format == None):
        archive_format = configuration ['archive_format']
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
