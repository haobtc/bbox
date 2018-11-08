from typing import Dict, Any, List, Union, Iterable, Optional, Tuple, Set
import os
import re
import time
import json
import sys
from aiobbox.utils import json_pp, json_to_str

Section = Dict[str, Any]
ConfigItem = Tuple[str, str, Any]

class SharedConfig:
    def __init__(self) -> None:
        self.sections: Dict[str, Section] = {}

    def replace_with(self, newticket:'SharedConfig') -> None:
        self.sections = newticket.sections

    def set(self, sec:str, key:str, value:Any) -> None:
        section = self.sections.setdefault(sec, {})
        section[key] = value

    def delete(self, sec: str, key: str) -> Optional[Section]:
        section = self.sections.get(sec)
        if section:
            return section.pop(key, None)
        else:
            return None

    def delete_section(self, sec: str) -> Optional[Section]:
        return self.sections.pop(sec, None)

    def get(self, sec: str, key: str, default: Any=None) -> Any:
        section = self.sections.get(sec)
        if section:
            return section.get(key, default)
        else:
            return default

    def get_chain(self, secs: List[str], key: str, default: Any=None) -> Any:
        for sec in secs:
            v = self.get(sec, key)
            if v:
                return v
        return default

    def get_strict(self, sec: str, key: str) -> Any:
        return self.sections[sec][key]

    def get_section(self, sec: str) -> Optional[Section]:
        return self.sections.get(sec)

    def get_section_strict(self, sec: str) -> Section:
        return self.sections[sec]

    def has_section(self, sec: str) -> bool:
        return sec in self.sections

    def has_key(self, sec: str, key: str) -> bool:
        return (self.has_section(sec) and
                key in self.sections[sec])

    def items(self, sec: str) -> Iterable[Tuple[str, Any]]:
        return self.sections[sec].items()

    def triple_items(self) -> Iterable[Tuple[str, str, Any]]:
        for sec, section in sorted(self.sections.items()):
            for key, value in sorted(section.items()):
                yield sec, key, value

    def clear(self) -> None:
        self.sections = {}

    def dump_json(self) -> str:
        return json_pp(self.sections)

    def compare_sections(self, new_sections: Section) -> Tuple[Set[ConfigItem], Set[ConfigItem]]:
        new_vset: Set[ConfigItem] = set()
        vset: Set[ConfigItem] = set()

        for sec, section in sorted(new_sections.items()):
            for key, value in sorted(section.items()):
                value = json_to_str(value)
                new_vset.add((sec, key, value))

        for sec, section in sorted(self.sections.items()):
            for key, value in sorted(section.items()):
                value = json_to_str(value)
                vset.add((sec, key, value))

        will_delete = vset - new_vset
        will_add = new_vset - vset

        new_2set = set((sec, key)
                       for (sec, key, value)
                       in will_add)

        will_delete = set((sec, key, value)
                      for (sec, key, value)
                      in will_delete
                      if (sec, key) not in new_2set)
        return will_delete, will_add

_shared = SharedConfig()
def get_sharedconfig() -> SharedConfig:
    return _shared
