#!/usr/bin/env python3
"""Minimal stdio MCP client for the zx84 emulator (..\\zx84, needs Node.js and npm install there).

  from zx84 import ZX84
  with ZX84() as zx:
      print(zx.call('model', target='128k'))
"""
import json, os, shutil, subprocess

ZX84_DIR = os.environ.get('ZX84', os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                               '..', '..', '..', 'zx84')))


def node_exe():
    n = shutil.which('node')
    if n:
        return n
    p = r'C:\Program Files\nodejs\node.exe'
    if os.path.exists(p):
        return p
    raise RuntimeError('node not found')


class ZX84:
    def __init__(self, model=None):
        args = [node_exe(), os.path.join('node_modules', 'tsx', 'dist', 'cli.mjs'), os.path.join('mcp', 'server.ts')]
        if model:
            args += ['--model', model]
        self.p = subprocess.Popen(args, cwd=ZX84_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding='utf-8', bufsize=1)
        self.id = 0
        self.request('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                    'clientInfo': {'name': 'sapi-fxs4', 'version': '1'}})
        self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + '\n')
        self.p.stdin.flush()

    def request(self, method, params):
        self.id += 1
        rid = self.id
        self.send({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params})
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError('zx84 server exited')
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get('id') == rid:
                if 'error' in msg:
                    raise RuntimeError(msg['error'])
                return msg['result']

    def call(self, tool, /, **args):
        """Call a tool, return its text output."""
        r = self.request("tools/call", {"name": tool, "arguments": args})
        text = '\n'.join(c.get('text', '') for c in r.get('content', []) if c.get('type') == 'text')
        if r.get('isError'):
            raise RuntimeError("%s: %s" % (tool, text))
        return text

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(5)
        except Exception:
            self.p.kill()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


if __name__ == '__main__':
    import sys
    with ZX84() as zx:
        print(zx.call(sys.argv[1], **json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
