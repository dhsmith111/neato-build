#!/usr/bin/env python3
"""drive.py — client for drive_daemon.py.

Usage:
  python drive.py status
  python drive.py explore [--duration N]
  python drive.py stop_explore
  python drive.py forward <mm> [--speed N]
  python drive.py back <mm> [--speed N]
  python drive.py pivot <degrees> <left|right>
  python drive.py arc <mm> <left|right>
  python drive.py stop
  python drive.py resume
  python drive.py set_param <key> <value>
  python drive.py get_params
  python drive.py bumper_events
  python drive.py decide
  python drive.py shutdown
"""
import argparse
import json
import socket
import sys

SOCKET_PATH = '/tmp/drive.sock'


def send(payload):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(90)
        s.connect(SOCKET_PATH)
        s.sendall((json.dumps(payload) + '\n').encode())
        data = b''
        while not data.endswith(b'\n'):
            chunk = s.recv(16384)
            if not chunk:
                break
            data += chunk
        s.close()
        return json.loads(data.decode().strip())
    except FileNotFoundError:
        return {'error': 'drive_daemon not running — start with: python drive_daemon.py'}
    except Exception as e:
        return {'error': str(e)}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('status')
    sub.add_parser('stop')
    sub.add_parser('resume')
    sub.add_parser('stop_explore')
    sub.add_parser('get_params')
    sub.add_parser('bumper_events')
    sub.add_parser('decide')
    sub.add_parser('shutdown')

    e = sub.add_parser('explore')
    e.add_argument('--duration', type=int, default=300, dest='duration_s')
    e.add_argument('--log', default=None, dest='log_path')

    f = sub.add_parser('forward')
    f.add_argument('mm', type=int)
    f.add_argument('--speed', type=int, default=None)

    b = sub.add_parser('back')
    b.add_argument('mm', type=int)
    b.add_argument('--speed', type=int, default=None)

    pv = sub.add_parser('pivot')
    pv.add_argument('degrees', type=int)
    pv.add_argument('direction', choices=['left', 'right'])
    pv.add_argument('--speed', type=int, default=None)

    a = sub.add_parser('arc')
    a.add_argument('mm', type=int)
    a.add_argument('direction', choices=['left', 'right'])
    a.add_argument('--inner', type=int, default=60, dest='inner_speed')
    a.add_argument('--outer', type=int, default=None, dest='outer_speed')

    sp = sub.add_parser('set_param')
    sp.add_argument('key')
    sp.add_argument('value', type=float)

    args = p.parse_args()

    payload = {'action': args.cmd}
    for k, v in vars(args).items():
        if k == 'cmd':
            continue
        if v is not None:
            payload[k] = v

    result = send(payload)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
