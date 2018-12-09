import re
import typing
import copy

class Option:
    LONG_PATTERN = re.compile(r"^--[a-zA-Z][a-zA-Z0-9-]+$")
    SHORT_PATTERN = re.compile(r"^-[a-zA-Z0-9]$")

    def __init__(self, name, **kwargs):
        assert Option.LONG_PATTERN.search(name)
        self.name = name
        self.short = kwargs.get("short", None)
        if self.short is not None:
            assert Option.SHORT_PATTERN.search(self.short)
        self.flag = bool(kwargs.get("flag", False))
        self.required = bool(kwargs.get("required", False))
        self.multiple = bool(kwargs.get("multiple", False))
        if self.multiple:
            assert "default" not in kwargs, "multiple value option can not have a default value"
            self.default = []
        else:
            self.default = kwargs.get("default", None)
            assert isinstance(self.default, (str, type(None))), "option default value must be of type str"
        self.help = kwargs.get("help", None)
        assert isinstance(self.help, (str, type(None))), "option default value must be of type str"

class OptionMap:
    def __init__(self):
        self.map: typing.Dict[str, Option] = {}

    def __getitem__(self, key):
        return self.map[key]
    
    def __contains__(self, key):
        return key in self.map
    
    def __copy__(self):
        c = OptionMap()
        c.map = copy.copy(self.map)
        return c
    
    def add(self, opt: Option):
        assert opt.name not in self.map
        assert opt.short is None or opt.short not in self.map
        self.map[opt.name] = opt
        if opt.short is not None:
            self.map[opt.short] = opt
    
    def get(self, name) -> Option:
        return self.map.get(name, None)
    
    def merge(self, m: "OptionMap"):
        for opt in set(m.map.values()):
            if opt.name in self.map:
                assert opt.flag == self.map[opt.name].flag
            else:
                self.map[opt.name] = opt
            if opt.short is None:
                continue
            if opt.short in self.map:
                assert opt.flag == self.map[opt.short].flag
                assert opt.name == self.map[opt.short].name
            else:
                self.map[opt.short] = opt
