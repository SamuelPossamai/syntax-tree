
from abc import ABC, abstractmethod

import re
import itertools

class NodeRule(ABC):

    class Modifier:

        def __init__(self, name: str):
            self.__name = name

        def getInfo(self, info_name):
            return None

        @abstractmethod
        def action(self, *args, **kwargs):
            pass

    @abstractmethod
    def applyRule(self, node, modifiers):
        pass

class RegexNodeRule(NodeRule):

    class NotInModifier(NodeRule.Modifier):

        def __init__(self, not_in_regex):
            self.__not_in_regex = not_in_regex

        def getInfo(self, info):
            if info == 'regex':
                return self.__not_in_regex

            return None

        def action(self, *args, **kwargs):

            if not args:
                return ()

            return RegexNodeRule._group_rangelist(
                match.span() for match in re.finditer(
                    self.__not_in_regex, args[0]))

    def __init__(self, types, re_match, re_filter=None, redo=False):

        self.__types = set(types)
        self.__redo = bool(redo)

        if isinstance(re_match, str):
            self.__re_match = (re_match,)
        else:
            self.__re_match = tuple(re_match)

        if re_filter is None:
            self.__re_filter = re_match
        else:
            if isinstance(re_filter, str):
                self.__re_filter = (re_filter,)
            else:
                self.__re_filter = tuple(re_filter)

            if len(self.__re_match) != len(self.__re_filter):
                raise ValueError('Match and filter size differ.')

    def applyRule(self, node, modifiers):

        if node.type_ not in self.__types:
            return False, (), ()

        val = node.value

        not_in_modifs = tuple(modif for modif in modifiers
                              if isinstance(modif, RegexNodeRule.NotInModifier))

        not_in_ranges = list(itertools.chain(
            *(modif.action(val) for modif in not_in_modifs)))

        not_in_ranges.sort()
        not_in_ranges = RegexNodeRule._group_rangelist(not_in_ranges)

        cur_string = val
        str_offset = 0
        str_list = []
        filter_list = []
        after = None
        for re_match, re_filter in zip(self.__re_match, self.__re_filter):

            match = re.search(re_match, cur_string)

            if match is None:
                return False, (), ()

            span = match.span()

            match_string = cur_string[span[0]:span[1]]

            match_filtered = re.search(re_filter, match_string)

            if match_filtered is None:
                return False, (), ()

            filtered_span = match_filtered.span()

            abs_filtered_span = (filtered_span[0] + span[0] + str_offset,
                                 filtered_span[1] + span[0] + str_offset)
            if RegexNodeRule._test_in_ranges(abs_filtered_span, not_in_ranges):
                print(abs_filtered_span, not_in_ranges)
                continue

            str_offset_diff = span[1]-(len(match_string) - filtered_span[1])

            before = cur_string[:span[0]+filtered_span[0]]
            after = cur_string[str_offset_diff:]
            match_string = match_string[filtered_span[0]:filtered_span[1]]

            str_list.append(before)
            filter_list.append(match_string)

            str_offset += str_offset_diff
            cur_string = after

        if after is None:
            return False, (), ()

        str_list.append(after)

        childs = []
        for child_str in str_list:

            cur_child = SyntaxTreeElement(child_str)

            node.addChild(cur_child)

        if len(filter_list) == 1:
            node.value = filter_list[0]
        else:
            node.value = tuple(filter_list)

        node_children = node.children
        if self.__redo:
            node_children = tuple(node_children)
        return True, node_children, node_children if self.__redo else ()

    @staticmethod
    def _test_in_ranges(val, range_list):

        for range_pair in range_list:
            if not(val[1] < range_pair[0] or val[0] > range_pair[1]):
                return True

        return False

    @staticmethod
    def _group_rangelist(range_list):

        range_list_iter = iter(range_list)

        cur_start, cur_end = next(range_list_iter, (None, None))

        if cur_start is None:
            return []

        result = []
        for start, end in range_list_iter:
            if start < cur_end:
                cur_end = end
            else:
                result.append((cur_start, cur_end))
                cur_start = start
                cur_end = end

        result.append((cur_start, cur_end))

        return result

class SyntaxTreeElement:

    def __init__(self, value, type_='Expression'):
        self.__value = value
        self.__children = []
        self.__type = type_

    @property
    def type_(self):
        return self.__type

    @type_.setter
    def type_(self, val):

        if not isinstance(val, str):
            raise TypeError('Expected \'str\'')

        self.__type = val

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, val):
        self.__value = val

    @property
    def children(self):
        return iter(self.__children)

    def addChild(self, el):
        self.__children.append(el)

    def _get_repr(self, depth=0):

        tab_seq = "\t"*depth

        if not self.__children:
            return f'{tab_seq}({repr(self.__value)}, \'{self.__type}\')'

        children_string = ",\n".join(
            (el._get_repr(depth + 1) for el in self.__children))
        return (f'{tab_seq}({repr(self.__value)}, \'{self.__type}\'): '
                f'[\n{children_string}\n{tab_seq}]')

    def __repr__(self):
        return self._get_repr()

    def isLeaf():
        return not self.__children

class SyntaxTree:

    def __init__(self, expr, leaf_rules=None, node_rules=None,
                 node_rules_modif=None):

        if leaf_rules:
            self.__leaf_rules = leaf_rules.copy()
        else:
            self.__leaf_rules = ()

        if node_rules:
            self.__node_rules = node_rules.copy()
        else:
            self.__node_rules = []

        if node_rules_modif:
            self.__node_rules_modif = node_rules_modif.copy()
        else:
            self.__node_rules_modif = {}

        self.__expr = expr
        self.__root = SyntaxTreeElement(expr)

        leaves = []
        redo_list = [self.__root]

        while redo_list:
            cur_leaves = redo_list
            redo_list = []
            for rule, rule_group in self.__node_rules:
                while(self.__apply_rule(cur_leaves,
                                        rule,
                                        self.__node_rules_modif.get(
                                            rule_group, ()),
                                        redo_list)):
                    pass

            leaves.extend(cur_leaves)
            cur_leaves = redo_list

        for leaf in leaves:
            for leaf_type, leaf_type_rule, leaf_type_filter in \
                self.__leaf_rules:

                if re.match(leaf_type_rule, leaf.value):
                    match = re.search(leaf_type_filter, leaf.value)
                    if match is None:
                        continue

                    span = match.span()

                    leaf.type_ = leaf_type
                    leaf.value = leaf.value[span[0]:span[1]]

                    break
            else:
                continue
                raise Exception(
                    f'Couldn\'t find a meaning for \'{leaf.value.strip()}\'')

    @staticmethod
    def __apply_rule(leaves, rule, modifiers, redo_list):

        modified = False

        for i, leaf in enumerate(leaves):

            applied, new_leaves, redo_list_add = rule.applyRule(leaf, modifiers)
            if applied is True:
                modified = True
                leaves[i:i + 1] = new_leaves

                redo_list.extend(redo_list_add)

        return modified


    def __repr__(self):
        return repr(self.__root)

leaf_types = [

    ("Integer", "^\s*[0-9]+\s*$", "[0-9]+"),
    ("Word", "^\s*[A-Za-z_][A-Za-z_0-9]*\s*$", "[A-Za-z_][A-Za-z_0-9]*"),
    ("Empty", "^\s*$", ''),
]

node_rules = [

    (RegexNodeRule(('Expression',),
                   (r'((\s|[A-Za-z0-9_(]|^)[+-](\s|[A-Za-z0-9_(]|$)|'
                    r'(\s|[A-Za-z0-9_(]|^)[+-](\s|[A-Za-z0-9_(]|$))'),
                   re_filter='[+-]'), 'op'),
    (RegexNodeRule(('Expression',),
                   r'^[^(]*(\s|[A-Za-z0-9_(]|^)[*/%](\s|[A-Za-z0-9_(]|$)',
                   re_filter='[*/%]'), 'op'),
    (RegexNodeRule(('Expression',), (r'^\s*\(', r'\)\s*$'),
                   re_filter=('\(', '\)'), redo=True), 'par'),
]

node_rules_modif = {

    'op': (RegexNodeRule.NotInModifier(r'\([^)]*\)'),)
}

syntax_tree = SyntaxTree('2 + 2*7 - 5 + 8*(3 + 5) + 3',
                         leaf_rules=leaf_types,
                         node_rules=node_rules,
                         node_rules_modif=node_rules_modif)

print(syntax_tree)
