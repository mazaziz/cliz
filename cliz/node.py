import re
import typing
import copy
from .option import Option, OptionMap

class CommandNotFound(Exception):
    def __init__(self, node, command):
        self.node = node
        self.command = command

class Handler:
    def __init__(self, callback, **kwargs):
        assert callable(callback)
        self.callback = callback
        self.help = kwargs.get("help", None)

    def __call__(self, opts):
        self.callback(opts)

class Node:
    NAME_PATTERN = re.compile(r"^[^-\s][^\s]*$")

    def __init__(self, name, **kwargs):
        self.name = name
        assert Node.NAME_PATTERN.search(name), "invalid name for node {}".format(self)
        self.prev: Node = None
        self.next: typing.Union[Argument, dict] = None
        self.options = OptionMap()
        self.handler = None
        self.help = kwargs.get("help", None)

    def __getitem__(self, key) -> "Node":
        if self.next is None:
            raise Exception("leaf node")
        elif isinstance(self.next, Argument):
            return self.next
        elif isinstance(self.next, dict):
            if key in self.next:
                return self.next[key]
            else:
                raise CommandNotFound(self, key)
        else:
            raise Exception("wtf")

    def __str__(self):
        return "{}[name='{}']".format(type(self).__name__, self.name)
    
    def _attach_argument(self, arg):
        assert arg.prev is None
        assert self.next is None
        self.next = arg
        arg.prev = self
    
    def _attach_command(self, cmd):
        assert cmd.prev is None
        if self.next is None:
            self.next = {}
        assert isinstance(self.next, dict)
        assert cmd.name not in self.next, "duplicate command: {}".format(cmd.name)
        self.next[cmd.name] = cmd
        cmd.prev = self

    def _attach_handler(self, h: Handler):
        assert self.handler is None
        self.handler = h

    def attach(self, *items):
        for item in items:
            if isinstance(item, Argument):
                self._attach_argument(item)
            elif isinstance(item, Command):
                self._attach_command(item)
            elif isinstance(item, Option):
                self.options.add(item)
            elif isinstance(item, Handler):
                self._attach_handler(item)
            elif callable(item):
                self._attach_handler(Handler(item))
            else:
                raise Exception("invalid item type '{}' to attach".format(type(item)))
        return self

    def get_options_down(self) -> OptionMap:
        down = copy.copy(self.options)
        if isinstance(self.next, Node):
            down.merge(self.next.get_options_down())
        elif isinstance(self.next, dict):
            for node in self.next.values():
                down.merge(node.get_options_down())
        return down

class Command(Node):
    pass

class Argument(Node):
    pass
