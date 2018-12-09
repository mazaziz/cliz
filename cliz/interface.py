from .node import Node, Command, Argument
from .option import Option, OptionMap
import cliz.error as error
from collections import deque
import typing

class Interface:
    def __init__(self, root: Command):
        assert isinstance(root, Command)
        self.root = root

    def print_help(self, node: Node):
        arguments = []
        argument_longest = 0
        usageq = deque([])
        pointer = node.prev
        while pointer is not None:
            if isinstance(pointer, Argument):
                usageq.appendleft(pointer.name.upper())
                arguments.append(pointer)
                argument_longest = max(argument_longest, len(pointer.name))
            else:
                usageq.appendleft(pointer.name)
            if pointer is self.root:
                pointer = None
            else:
                pointer = pointer.prev

        def _usage_right(n: Node):
            v = n.name
            if n.next is None:
                return v
            elif isinstance(n.next, Node):
                if n.handler is None:
                    return "{} {}".format(v, _usage_right(n.next))
                else:
                    return "{} [{}]".format(v, _usage_right(n.next))
            elif isinstance(n.next, dict):
                if n.handler is None:
                    return "{} <command>".format(v)
                else:
                    return "{} [<command>]".format(v)
            else:
                raise Exception("invalid next obj: {}".format(n.next))
        usageq.append(_usage_right(node))

        print("Usage: {}".format(" ".join(usageq)))
        if node is self.root or (isinstance(node, Command) and node.help is not None and node.handler is not None):
            print("")
            print(node.help)

        # print help options
        if node.handler is not None:
            items = []
            longest = 0
            for opt in set(node.get_options_up().map.values()):
                items.append([
                    "  " if opt.short is None else opt.short,
                    " " if opt.short is None else ",",
                    opt.name,
                    "" if opt.help is None else opt.help,
                    "" if not isinstance(opt.default, str) else "[default: {}]".format(opt.default)
                ])
                longest = max(longest, len(opt.name))
            if len(items) > 0:
                print("\nOptions:")
                for i in items:
                    print("  {}{} {:{fill}}  {} {}".format(i[0], i[1], i[2], i[3], i[4], fill=longest))
        
        # arguments
        if len(arguments) > 0:
            print("\nArguments:")
            for arg in arguments:
                print("  {}  {}".format(arg.name.upper(), "" if arg.help is None else str(arg.help)))

        # commands
        if isinstance(node.next, dict):
            longest = 0
            for cmd in node.next.values():
                longest = max(longest, len(cmd.name))
            if longest > 0:
                print("\nCommands:")
                for cmd in node.next.values():
                    print("  {:{fill}}  {}".format(cmd.name, "" if cmd.help is None else str(cmd.help), fill=longest))

    def normalize_user_options(self, node: Node, user_opts: dict):
        node_options = node.get_options_up()

        # check for user options which are not allowed on the node
        for name in user_opts:
            if not name.startswith("-"):
                continue
            assert name in node_options, "unknown option: {}".format(name)

        # validate leaf options
        normalized = {}
        for opt in set(node_options.map.values()):
            if opt.flag:
                normalized[opt.name] = user_opts.get(opt.name, 0)
                if opt.short is not None:
                    normalized[opt.name] += user_opts.get(opt.short, 0)
                if not opt.multiple:
                    assert normalized[opt.name] < 2, "multiple '{}' option is not allowed".format(opt.name)
            else:
                normalized[opt.name] = []
                for v in user_opts.get(opt.name, []):
                    normalized[opt.name].append(v)
                if opt.short is not None:
                    for v in user_opts.get(opt.short, []):
                        normalized[opt.name].append(v)
                if len(normalized[opt.name]) > 1:
                    assert opt.multiple, "multiple '{}' option is not allowed".format(opt.name)
                elif 1 == len(normalized[opt.name]):
                    if not opt.multiple:
                        normalized[opt.name] = normalized[opt.name][0]
                elif opt.required:
                    raise Exception("missing required option '{}'".format(opt.name))
                else:
                    normalized[opt.name] = opt.default
        return normalized

    def run(self, args: list):
        argq = deque(args)
        interface_option_map = self.root.get_options_down()
        user_raw_options = {}

        def save_user_option(name):
            if name not in interface_option_map:
                raise error.UnknownOption(name)
            if interface_option_map[name].flag:
                user_raw_options[name] = 1 + user_raw_options.get(name, 0)
            else:
                try:
                    option_value = argq.popleft()
                except:
                    raise error.MissingOptionValue(name)
                if option_value.startswith("-"):
                    raise error.MissingOptionValue(name)
                user_raw_options.setdefault(name, []).append(option_value)

        pathq = deque([])
        while len(argq) > 0:
            token = argq.popleft()
            if not token.startswith("-"):
                pathq.append(token)
            elif token == "--help":
                user_raw_options["--help"] = 1 + user_raw_options.get("--help", 0)
            elif token.startswith("--"):
                if not Option.LONG_PATTERN.search(token):
                    raise error.InvalidOption(token)
                save_user_option(token)
            elif len(token) > 2:
                for c in reversed(token[1:]):
                    argq.appendleft("-{}".format(c))
            else:
                if not Option.SHORT_PATTERN.search(token):
                    raise error.InvalidOption(token)
                save_user_option(token)
        
        # walk to find leaf node
        head = self.root
        positional_args = {}
        while len(pathq) > 0:
            segment = pathq.popleft()
            assert head.next is not None, "unexpected arg: {}".format(segment)
            if isinstance(head.next, Argument):
                head = head.next
                positional_args[head.name] = segment
            elif isinstance(head.next, dict):
                if segment not in head.next:
                    raise Exception("unknown command: {}".format(segment))
                head = head.next[segment]
            else:
                raise Exception("wtf")
        
        if "--help" in user_raw_options:
            self.print_help(head)
        elif head.handler is not None:
            callp = self.normalize_user_options(head, user_raw_options)
            callp.update(positional_args)
            head.handler(callp)
        elif head.next is None:
            raise Exception("cli error: no handler found")
        elif isinstance(head.next, Argument):
            self.print_help(head)
            print("\nERROR: missing argument: {}".format(head.next.name))
        elif isinstance(head.next, dict):
            self.print_help(head)
            print("\nERROR: missing command")
        else:
            raise Exception("wtf")
