
from abc import ABC, abstractmethod

import re

class NodeRule(ABC):

    @abstractmethod
    def applyRule(self, node):
        pass

class RegexNodeRule(NodeRule):

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

    def applyRule(self, node):

        if node.type_ not in self.__types:
            return False, (), ()

        val = node.value

        cur_string = val
        str_list = []
        filter_list = []
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

            before = cur_string[:span[0]+filtered_span[0]]
            after = cur_string[span[1]-(len(match_string) - filtered_span[1]):]
            match_string = match_string[filtered_span[0]:filtered_span[1]]

            str_list.append(before)
            filter_list.append(match_string)

            cur_string = after

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

    def __init__(self, expr, leaf_rules=None, node_rules=None):

        if leaf_rules:
            self.__leaf_rules = leaf_rules.copy()
        else:
            self.__leaf_rules = ()

        if node_rules:
            self.__node_rules = node_rules.copy()
        else:
            self.__node_rules = ()

        self.__node_rules = node_rules or ()
        self.__expr = expr
        self.__root = SyntaxTreeElement(expr)

        leaves = []
        redo_list = [self.__root]

        while redo_list:
            cur_leaves = redo_list
            redo_list = []
            for rule in self.__node_rules:
                while(self.__apply_rule(cur_leaves, rule, redo_list)):
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
    def __apply_rule(leaves, rule, redo_list):

        modified = False

        for i, leaf in enumerate(leaves):

            applied, new_leaves, redo_list_add = rule.applyRule(leaf)
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

    RegexNodeRule(('Expression',),
                  (r'(^[^(]*(\s|[A-Za-z0-9_(]|^)[+-](\s|[A-Za-z0-9_(]|$)|'
                   r'(\s|[A-Za-z0-9_(]|^)[+-](\s|[A-Za-z0-9_(]|$)[^)]$)'),
                  re_filter='[+-]'),
    RegexNodeRule(('Expression',),
                  r'^[^(]*(\s|[A-Za-z0-9_(]|^)[*/%](\s|[A-Za-z0-9_(]|$)',
                  re_filter='[*/%]'),
    RegexNodeRule(('Expression',), (r'^\s*\([^)]*\)\s*$', r'\)'),
                  re_filter=('\(', '\)'), redo=True),
]

syntax_tree = SyntaxTree('2 + 4 + 2*7 + 12 - 5 + 8*(3 + 5) + 3',
                         leaf_rules=leaf_types,
                         node_rules=node_rules)

print(syntax_tree)
