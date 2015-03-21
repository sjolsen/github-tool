#!/usr/bin/python3

import uritemplate
import urllib.parse
import urllib.request
import json
import os.path

conf_files = [os.path.relpath ('config.json')]
default_configuration = {
    'connection_method' : 'https',
    'api_host'          : 'api.github.com',
    'api_root'          : '/',
    'archive_format'    : 'tarball'
}

def load_configuration ():
    configuration = default_configuration.copy ()
    for filename in conf_files:
        try:
            with open (filename, 'r') as file:
                configuration.update (json.load (file))
        except FileNotFoundError:
            pass
    return configuration


def api_url (config, *path):
    method  = config ['connection_method']
    host    = config ['api_host']
    root    = config ['api_root']
    base    = urllib.parse.urlunsplit ((method, host, root, '', ''))
    relpath = '/'.join (map (lambda s: urllib.parse.quote (s, safe=''), path))
    url     = urllib.parse.urljoin (base, relpath)
    return url

def api_get (config, url):
    # TODO: Error checking
    response = urllib.request.urlopen (url)
    raw_data = response.read ()
    return json.loads (raw_data.decode ('utf-8'))

def get_repo (config, api, owner, repo_name):
    url = uritemplate.expand (api ['repository_url'], {
        'owner' : owner,
        'repo'  : repo_name
    })
    return api_get (config, url)

def save_archive (config, repo, directory=None, filename=None, archive_format=None, ref=None):
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
