# based on https://github.com/MaineKuehn/rpconnect
# @author: MaineKuehn, Jeff Chern
# @date: 2022-1-2
import builtins
import json
import logging
import signal
import socket
import sys


__all__ = ('RpcServer', 'RpcClient')


def read_socket(source_socket, num_bytes):
    message = b""
    while True:
        chunk = source_socket.recv(num_bytes - len(message))
        message += chunk
        if not chunk or len(message) == num_bytes:
            return message


def read_message(source_socket):
    message_length = int.from_bytes(read_socket(source_socket, 16), 'little')
    raw_message = read_socket(source_socket, message_length)
    return raw_message.decode()


def send_message(target_socket, message: str):
    raw_message = message.encode()
    target_socket.sendall(len(raw_message).to_bytes(16, 'little'))
    target_socket.sendall(raw_message)


class RpcServer(object):

    def __init__(self, host: str='localhost', port: int=8800):
        self.host = host
        self.port = port
        self._closed = False # this line should come before creating a socket.
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, self.port))
        self._socket.listen(5)
        self._payloads = {}  # name => callable

    def register(self, payload: callable, name: str=None):
        if name is None:
            name = payload.__name__
        self._payloads[name] = payload

    register_function = register

    def run(self):
        signal.signal(signal.SIGINT, lambda x, y: sys.exit(1))
        logging.info('starting RPC server [%s:%i]', self.host, self.port)
        while not self.closed:
            (clientsocket, address) = self._socket.accept()
            logging.debug('new connection: %s', address)
            # directly call function, but not via threading or multiprocess
            self._handle_request(clientsocket, address)

    serve_forever = run

    def _handle_request(self, clientsocket, address):
        logging.debug('[%s] handling connection', address)
        try:
            message = read_message(clientsocket)
            data = json.loads(message)
            payload_name = data['_name']
            payload_args = data['args']
            payload_kwargs = data['kwargs']
            logging.debug('[%s]: %s(*%s, **%s)', address, payload_name,
                payload_args, payload_kwargs)
            result = self._payloads[payload_name](*payload_args, **payload_kwargs)
            logging.debug('[%s]: %s', address, result)
            send_message(clientsocket, self._format_result(result))
        except Exception as err:
            logging.exception('[%s]: Exception', address)
            send_message(clientsocket, self._format_exception(err))
        clientsocket.close()

    @staticmethod
    def _format_result(result):
        data = {'type': 'result', 'content': result}
        return json.dumps(data)

    @staticmethod
    def _format_exception(err, message=''):
        data = {
            'type': 'error',
            'exc_type': err.__class__.__name__,
            'message': message or str(err)
        }
        return json.dumps(data)

    @property
    def closed(self):
        return self._closed

    @closed.setter
    def closed(self, value):
        if (not value) and self._closed:
            raise ValueError('cannot restart a server')

        if not self._closed:
            logging.info('stopping RPC server [%s:%i]', self.host, self.port)
            # to avoid memory leak, use two steps to close socket.
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                self._socket.close()
            except OSError:
                pass

            del self._socket
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.debug('__exit__: %s %s', exc_type, exc_val)
        self.closed = True
        return False

    def __del__(self):
        self.closed = True


class RpcClient(object):

    def __init__(self, host: str='localhost', port: int=8800):
        self.host = host
        self.port = port

    def __getattr__(self, attr):
        def _caller(*args, **kwargs):
            logging.debug("[Server %s:%i][Method %s][Args %s][Kwargs %s]",
                self.host, self.port, attr, args, kwargs)
            data = {'_name': attr, 'args': args, 'kwargs': kwargs}
            message = json.dumps(data)
            try:
                serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # serversocket.settimeout(self.timeout)
                serversocket.connect((self.host, self.port))
                send_message(serversocket, message)
                raw_result = read_message(serversocket)
                serversocket.close()
                reply = json.loads(raw_result)
                if reply['type'] == 'result':
                    return reply['content']
                elif reply['type'] == 'error':
                    exc = getattr(builtins, reply['exc_type'], None)
                    if isinstance(exc, Exception):
                        raise exc(reply['message'])
                    raise ValueError(f'{reply["exc_type"]}: {reply["message"]}')
                else:
                    raise ValueError(f'malformed reply: {reply}')
            except Exception as err:
                return err, None
        return _caller

