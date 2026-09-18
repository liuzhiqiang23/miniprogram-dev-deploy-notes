#!/usr/bin/env python
"""Run a shell command on a remote server over SSH.

The password lives only in the SSH_PW environment variable, never on disk.
Once a key is installed on the server you can drop this and use plain ssh/scp.

Usage:
    SSH_PW=... python ssh_run.py "uname -a"
    SSH_PW=... python ssh_run.py -f some_script.sh
    SSH_PW=... python ssh_run.py -u root "whoami"
    SSH_PW=... python ssh_run.py --put local.txt /tmp/x

Requires: pip install paramiko
"""
import os
import sys

import paramiko

HOST = os.environ.get('SSH_HOST', '203.0.113.10')
PORT = int(os.environ.get('SSH_PORT', '22'))
USER = os.environ.get('SSH_USER', 'ubuntu')


def connect(user=USER):
    pw = os.environ.get('SSH_PW')
    if not pw:
        sys.exit('SSH_PW is not set')
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=user, password=pw,
                timeout=25, banner_timeout=25, auth_timeout=25,
                look_for_keys=False, allow_agent=False)
    return cli


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)

    user = USER
    if args[0] == '-u':
        user = args[1]
        args = args[2:]

    cli = connect(user)

    if args[0] == '--put':
        sftp = cli.open_sftp()
        sftp.put(args[1], args[2])
        print('uploaded %s -> %s' % (args[1], args[2]))
        sftp.close()
        cli.close()
        return

    if args[0] == '-f':
        with open(args[1], 'r', encoding='utf-8') as fh:
            cmd = fh.read()
    else:
        cmd = args[0]

    _in, out, err = cli.exec_command(cmd, timeout=1800, get_pty=False)
    o = out.read().decode('utf-8', 'replace')
    e = err.read().decode('utf-8', 'replace')
    rc = out.channel.recv_exit_status()
    sys.stdout.write(o)
    if e.strip():
        sys.stdout.write('\n--- stderr ---\n' + e)
    sys.stdout.write('\n--- exit=%d ---\n' % rc)
    cli.close()


if __name__ == '__main__':
    main()
