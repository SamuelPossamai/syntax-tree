
import re

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
        return self.__children

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

        leafs = [self.__root]

        while(self.__split_single(leafs, r'\b\s*[+-]\s*\b', '[+-]')):
            pass

        while(self.__split_single(leafs, r'\b\s*[*/%]\s*\b', '[*/%]')):
            pass

        for leaf in leafs:
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
                raise Exception(
                    f'Couldn\'t find a meaning for \'{leaf.value.strip()}\'')

    @staticmethod
    def __split_single(leafs, symbol_match, symbol_filter):

        modified = False

        for i, leaf in enumerate(leafs):
            val = leaf.value

            match = re.search(symbol_match, val)

            if match is None:
                continue

            span = match.span()

            match_string = val[span[0]:span[1]]

            match_filtered = re.search(symbol_filter, match_string)

            if match_filtered is None:
                continue

            filtered_span = match_filtered.span()

            before = val[:span[0]+filtered_span[0]]
            after = val[span[1]-(len(match_string) - filtered_span[1]):]
            match_string = match_string[filtered_span[0]:filtered_span[1]]

            leaf.value = match_string
            child_before = SyntaxTreeElement(before)
            child_after = SyntaxTreeElement(after)

            leaf.addChild(child_before)
            leaf.addChild(child_after)

            leafs[i:i + 1] = child_before, child_after

            modified = True

        return modified


    def __repr__(self):
        return repr(self.__root)

def split_single(leafs, symbol_match, symbol_filter):

    modified = False

    for i, leaf in enumerate(leafs):
        val = leaf.value

        match = re.search(symbol_match, val)

        if match is None:
            continue

        span = match.span()

        match_string = val[span[0]:span[1]]

        match_filtered = re.search(symbol_filter, match_string)

        if match_filtered is None:
            continue

        filtered_span = match_filtered.span()

        before = val[:span[0]+filtered_span[0]]
        after = val[span[1]-(len(match_string) - filtered_span[1]):]
        match_string = match_string[filtered_span[0]:filtered_span[1]]

        leaf.value = match_string
        child_before = SyntaxTreeElement(before)
        child_after = SyntaxTreeElement(after)

        leaf.addChild(child_before)
        leaf.addChild(child_after)

        leafs[i:i + 1] = child_before, child_after

        modified = True

    return modified

leaf_types = [

    ("Integer", "^\s*[0-9]+\s*$", "[0-9]+"),
    ("Word", "^\s*[A-Za-z_][A-Za-z_0-9]*\s*$", "[A-Za-z_][A-Za-z_0-9]*")
]

syntax_tree = SyntaxTree('2 + 4 + 2*7 + 12 - 5',
                         leaf_rules=leaf_types)

print(syntax_tree)
