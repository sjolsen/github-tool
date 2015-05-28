#!/usr/bin/python3

import base64
import copy
import uritemplate
import urllib.parse
import urllib.request
import json
import os.path

# A list of configuration files to use, by pathname. Currently, the only
# configuration file looked for is one named 'config.json' in the current
# working directory. Each file should contain a json object which, when
# converted to a Python dictionary, is suitable as an argument to config.update.
conf_files = [os.path.relpath ('config.json')]

# The default configuration. These settings may be overridden using a
# configuration file. The possible options are:
#
# - connection_method: One of 'http' or 'https', the method used to make API
#   requests.
#
# - api_host: The FQDN of the server hosting the API. By default, GitHub's own
#   server is used.
#
# - api_root: The path on the API server that serves the API root.
#
# - archive_format: The default format to use when downloading
#   archives. Possible values are 'tarball' for a GZip'd tar archive and
#   'zipball' for a ZIP archive.
#
# - authentication: The authentication method to use. A value of None indicates
#   no authentication. Otherwise, this should be a dictionary with an entry with
#   key 'type'. The only currently valid value for this key is 'basic', and the
#   dictionary must contain 'username' and 'password' fields, with the obvious
#   semantics.
#
default_config = {
    'connection_method' : 'https',
    'api_host'          : 'api.github.com',
    'api_root'          : '/',
    'archive_format'    : 'tarball',
    'authentication'    : None
}
config = None

# The default API cache. Fields are described at their point of use.
default_cache = {
    'api_root'     : None,
    'auth_headers' : {
        id(None) : {}
    }
}
cache = None

# Loads all settings and clears the cache. This must be called at least once
# before using the rest of the code here.
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

# Caching function for retreiving the root API object. This object allows access
# to the entire GitHub API on the configured server by means of URI templates.
def api_root ():
    # cache ['api_root']: The root API object.
    if (cache ['api_root'] == None):
        cache ['api_root'] = api_get (api_url ())
    return cache ['api_root']

# Caching function for authorization headers. These headers are necessary to
# provide the server with authentication parameters, if using basic
# authentication.
def auth_headers (auth):
    # cache ['auth_headers']: A dictionary mapping authorization information
    # objects to their respective headers. These headers are suitable for the
    # headers argument to urllib.request.Request.
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

# Variadic function which uses its arguments to construct a URL according to the
# current configuration. For example, under the default configuration, the call
#
#   api_url ('asdf', 'foo', 'bar')
#
# would yield
#
#   'https://api.github.com/asdf/foo/bar'.
#
# Path components are quoted where necessary.
def api_url (*path):
    method  = config ['connection_method']
    host    = config ['api_host']
    root    = config ['api_root']
    base    = urllib.parse.urlunsplit ((method, host, root, '', ''))
    relpath = '/'.join (map (lambda s: urllib.parse.quote (s, safe=''), path))
    url     = urllib.parse.urljoin (base, relpath)
    return url

# Retrieves the JSON object served at the given URL.
def api_get (url):
    # TODO: Error checking
    headers  = auth_headers (config ['authentication'])
    request  = urllib.request.Request (url, headers=headers)
    response = urllib.request.urlopen (request)
    raw_data = response.read ()
    return json.loads (raw_data.decode ('utf-8'))

# Retrieves the object describing the repository owned by the given owner under
# the given name.
def get_repo (owner, repo_name):
    url = uritemplate.expand (api_root () ['repository_url'], {
        'owner' : owner,
        'repo'  : repo_name
    })
    return api_get (url)

# Saves a repository to disk in archive format. The arguments are as follows:
#
# - repo: The object describing the repository to save (e.g., the return value
#   of get_repo).
#
# - directory: The directory in which to save the archive. Defaults to the
#   current working directory.
#
# - filename: The filename to give the saved archive. Defaults to the name of
#   the repository plus the ref (if suppiled), and an appropriate extension.
#
# - archive_format: The format in which to save the archive. Possible values are
#   'tarball' and 'zipball'. Default is determined by the configuration.
#
# - ref: The git ref to fetch. By default, HEAD on branch master is downloaded.
#
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
        suffix = '-{}'.format (ref) if ref else ''
        filename = '{}{}.{}'.format (repo ['name'], suffix, extensions [archive_format])

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

# Program driver with simple options and minimal error handling. This is what
# should be replaced for scripting purposes (alternatively, the above code could
# be put into a module).
def main ():
    arg_parser = argparse.ArgumentParser ()
    arg_parser.add_argument ('command', help='one of "get"')
    arg_parser.add_argument ('owner', help='owner of "repo"')
    arg_parser.add_argument ('repo', help='repo owned by "owner"')
    arg_parser.add_argument ('--archive-type', help='one of "tarball", "zipball"')
    arg_parser.add_argument ('--save-dir', help='directory in which to save archive')
    arg_parser.add_argument ('--filename', help='filename to give saved archive')
    arg_parser.add_argument ('--ref', help='git ref to save')
    args = arg_parser.parse_args ()

    if (args.command == 'get'):
        load_configuration ()
        repo = get_repo (args.owner, args.repo)
        save_archive (
            repo,
            directory      = args.save_dir,
            filename       = args.filename,
            archive_format = args.archive_type,
            ref            = args.ref
        )
    else:
        raise

if __name__ == '__main__':
    main ()
else:
    load_configuration ()
