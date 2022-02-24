# minirpc

A minimal and efficient JsonRPC library for Python.

The implementation is based on [rpconnect](https://github.com/MaineKuehn/rpconnect). In this fork, I have made some improvements, such as similar usage like `xmlrpc` in Python standard libray (see usage below), and fixed many bugs.

Also, to make the behavior similar to `xmlrpc`, I have changed the running mode to calling functions directly, but not by forking a process or spawning a thread.

## Dependency

Just standard library of Python.

## Usage

### server side

```python
from minirpc import RpcServer

def _echo(info):
    return f'hello {info}'

server = RpcServer("localhost", 8800)
server.register_function(_echo, "echo")
server.serve_forever()
```
or

```python
with RpcServer("localhost", 8800) as server:
    server.register(_echo, "echo")
    server.run()
```

### client side

```python
from minirpc import RpcClient

client = RpcClient("localhost", 8800)

msg = client.echo('world!')
print(msg)
# 'hello world!'
```

