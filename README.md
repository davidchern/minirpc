# minrpc

A minimal and efficient Json RPC library for Python.

The implementation is based on [rpconnect](https://github.com/MaineKuehn/rpconnect). In this fork, I have made some improvements, such as similar usage like `xmlrpc` in Python standard libray, and fixed many bugs. Also, to make the behavior similar to `xmlrpc`, I have changed the running mode to calling method directly, but not via a forked process.

## Dependency

Just standard library of Python.

## Usage

### server side

```python
from minirpc import RpcServer

def echo(info):
    return f'hello {info}'

server = RpcServer("localhost", 8800)
server.register_function(echo, "echo")
server.serve_forever()
```

### client side

```python
from minirpc import RpcClient

client = RpcClient("localhost", 8800)

msg = client.echo('world!')
print(msg)
# 'hello world!'
```

