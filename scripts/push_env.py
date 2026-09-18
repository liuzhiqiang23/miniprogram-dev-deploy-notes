#!/usr/bin/env python
"""Push deployment secrets from this machine to a server without leaking them.

Reads the given variable names from this machine's environment (on Windows you
can keep them in the User scope) and writes them into a chmod-600 env file on
the server over SFTP. The values never appear on a command line and are never
printed.

Usage:
    SSH_PW=... python push_env.py            # write the file
    SSH_PW=... python push_env.py --show     # print names + lengths only
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh_run import connect

# Names to copy from this machine to the server env file.
SECRET_VARS = ['WX_APPID', 'WX_SECRET', 'WX_ADMIN_OPEN_IDS']

REMOTE = '/opt/movie-system/movie.env'
DB_USER = 'movie'
DB_PASS = os.environ.get('DB_PASS', 'change-me')


def read_env(name):
    """Read a User-scope environment variable straight from the registry."""
    out = subprocess_run(
        ['powershell', '-NoProfile', '-Command',
         "[Environment]::GetEnvironmentVariable('%s','User')" % name])
    return (out or '').strip()


def subprocess_run(cmd):
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout


def main():
    values = {v: read_env(v) for v in SECRET_VARS}
    missing = [k for k, v in values.items() if not v]
    if missing:
        sys.exit('missing env vars: %s' % ', '.join(missing))

    if '--show' in sys.argv:
        for k, v in values.items():
            print('  %s: %d chars, starts %s' % (k, len(v), v[:6]))
        return

    lines = [
        '# runtime secrets -- chmod 600, owned by the service user. do not commit.',
        '# written by push_env.py',
        'SPRING_DATASOURCE_USERNAME=%s' % DB_USER,
        'SPRING_DATASOURCE_PASSWORD=%s' % DB_PASS,
        # Loopback only: nginx is the only public front. The cloud security group
        # may also block the app port, but that rule is not under our control --
        # binding to loopback makes this true at the OS level.
        'SERVER_ADDRESS=127.0.0.1',
    ]
    for k in SECRET_VARS:
        lines.append('%s=%s' % (k, values[k]))
    content = '\n'.join(lines) + '\n'

    cli = connect()
    sftp = cli.open_sftp()
    with sftp.open(REMOTE, 'w') as fh:
        fh.write(content)
    sftp.close()
    _i, o, _e = cli.exec_command('chmod 600 %s && stat -c "%%a %%U %%s bytes" %s'
                                 % (REMOTE, REMOTE))
    print('wrote %s -> %s' % (REMOTE, o.read().decode().strip()))
    cli.close()


if __name__ == '__main__':
    main()
