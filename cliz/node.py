import re
import typing
import copy
from .option import Option, OptionMap

class CommandNotFound(Exception):
    def __init__(self, node, command):
        self.node = node
        self.command = command

class Node:
    NAME_PATTERN = re.compile(r"^[^-\s][^\s]*$")

    def __init__(self, name, **kwargs):
        self.name = name
        assert Node.NAME_PATTERN.search(name), "invalid name for node {}".format(self)
        self.prev: Node = None

        # options
        self.options = OptionMap()
        for opt in kwargs.get("options", []):
            self.options.add(opt)

        # next node(s)
        self.next: typing.Union[Argument, dict] = None
        _next = kwargs.get("next", [])
        if not isinstance(_next, list):
            _next = [_next]
        for i in _next:
            self.attach(i)

        # handler
        self.handler = kwargs.get("handler", None)
        if self.handler is not None:
            assert callable(self.handler), "given handler '{}' is not callable".format(self.handler)

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

    def attach(self, node):
        if isinstance(node, Argument):
            assert node.prev is None
            assert self.next is None
            self.next = node
            node.prev = self
        elif isinstance(node, Command):
            assert node.prev is None
            if self.next is None:
                self.next = {}
            assert isinstance(self.next, dict)
            assert node.name not in self.next, "duplicate command: {}".format(node.name)
            self.next[node.name] = node
            node.prev = self
        else:
            raise Exception("invalid node type '{}'".format(type(node)))
    
    def get_options_down(self) -> OptionMap:
        down = copy.copy(self.options)
        if isinstance(self.next, Node):
            down.merge(self.next.get_options_down())
        elif isinstance(self.next, dict):
            for node in self.next.values():
                down.merge(node.get_options_down())
        return down
    
    def get_options_up(self) -> OptionMap:
        up = copy.copy(self.options)
        pointer = self.prev
        while pointer is not None:
            up.merge(pointer.options)
            pointer = pointer.prev
        return up

class Command(Node):
    pass

class Argument(Node):
    pass
