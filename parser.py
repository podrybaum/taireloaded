import inspect
from ast_classes import BinaryExpression, ConditionalGoto, FilterLine, ResponseLine, MultipleChoiceBlock, BlockEnd
from bus import Bus
from collections import namedtuple
from dispatch_dict import DISPATCH_DICT
from tai_exceptions import SyntaxErr, ValueErr
from tokens import OperatorToken, Token, VarRef, StringToken
from typing import List

# NOTE: When we return "filters" the list we return has conditional expressions + AND/OR operators in reverse polish notation.
#       Need to remember this for the interpreter
#       We don't have any precedence handling for arithmetic operators because the syntax doesn't currently allow
#       arbitrarily long arithmetic expressions.  Support to be added in the future.

Mark = namedtuple("Mark", ["pointer", "position", "last"])


class Parser:
    """Parser(stream: List[Token])"""

    def __init__(self, stream: List[Token]):
        self.stream = stream
        self.pointer = 0
        self.blocks = []
        self.end_tease = False
        self.last = None  # <- keep a copy of last consumed token here, sometimes needed for error handling
        self.position = (0, 0, "")  # <- tuple with the line, column and filename of the last consumed token
        self.debug = True
        Bus.sub("end_tease", lambda: setattr(self, "end_tease", True))

    def peek(self):
        return self.stream[self.pointer + 1]

    def mark(self):
        """Back up the pointer position, line/col position and last consumed token."""
        return Mark(self.pointer, self.position, self.last)

    def reset(self, mark):
        """Backtrack after incomplete match, restoring pointer position, line/col position and last consumed token."""
        self.pointer = mark.pointer
        self.position = mark.position
        self.last = mark.last

    def expect(self, string) -> Token | bool:
        """If the lookahead token's value OR ttype attribute matches the string passed, consume and return it."""
        caller = inspect.currentframe().f_back.f_code.co_name
        if self.peek().ttype == string or self.peek().value == string:
            token = self.stream[self.pointer + 1]
            self.pointer += 1
            self.last = token
            self.position = token.get_position()
            if self.debug:
                print(f"expect called by {caller}: returning {token} with pointer at {self.pointer}")
            if self.position[0] == 154:
                pass
            return token
        return False

    def run(self):
        while self.pointer < len(self.stream) and not self.end_tease:
            block = self.block()
            if block is False:
                if self.pointer < len(self.stream):
                    print(f"Parse incomplete. {self.pointer} of {len(self.stream)} tokens handled.")
                break
            if isinstance(block, FilterLine) and not block.stmts:
                continue  # This is an empty line so we just discard it here.
            else:
                self.blocks.append(block)

    def block(self):
        mark = self.mark()
        if stmts := self.stmts():  # TODO: make an AST class for multiple choice blocks
            # IMPORTANT: We need to check for the multiple choice block first, because its first line
            #            could also match a FilterLine with empty filters.  If FilterLine were to consume
            #            this line, we'd be left with a broken multiple choice block.
            if self.expect("NEWLINE"):
                if responses := self.responses():
                    block = MultipleChoiceBlock(stmts, responses)
                    if block_end := self.block_end():
                        block.block_end = block_end
                        return block
                    SyntaxError(
                        "Expected @AcceptAnswer or @DifferentAnswer to end multiple choice block", *self.position
                    ).throw()
        self.reset(mark)
        if block := self.filterline():
            return block
        return False

    def filterline(self):
        filters = self.filters() or None  # empty filters is acceptable.
        if filters:  # if filters is non-empty, stmts must also be non-empty
            if stmts := self.stmts():
                if self.expect("NEWLINE"):
                    return FilterLine(filters, stmts)
                SyntaxErr("Expected statement", *self.position).throw()
        stmts = self.stmts()  # filters is empty, so empty stmts is acceptable
        if self.expect("NEWLINE"):
            return FilterLine(
                None, stmts
            )  # if stmts is empty, this is FilterLine(None, None).  in other words, blank line.
        return False

    def responses(self):
        responses = []
        while True and not self.end_tease:
            if response := self.responseline():
                responses.append(response)
            else:
                break
        if len(responses) >= 2:
            return responses
        if len(responses) == 1:
            SyntaxErr("Multiple choice block requires more than one response line", *self.position).throw()
        else:
            return False

    def responseline(self):
        if self.expect("LBRACKET"):
            if list_strings := self.list_strings():
                if self.expect("RBRACKET"):
                    if stmts := self.stmts():
                        if self.expect("NEWLINE"):
                            return ResponseLine(list_strings, stmts)
                        # can't really fail here, as if there's no newline it's just more stmts
                    SyntaxErr("Expected instruction after multiple choice option", *self.position).throw()
                SyntaxErr("Unmatched delimiter: expected ']'", *self.position).throw()
            SyntaxErr("Expected multiple choice option list", *self.position).throw()
        return False

    def list_strings(self):
        strings = []
        while True and not self.end_tease:
            if string := self.expect("STRING"):
                strings.append(string)
            elif int := self.expect("INTEGER"):
                strings.append(StringToken(*int.get_position(), int.value))
            elif self.expect("COMMA"):
                continue
            else:
                break
        if len(strings) > 0:
            return strings
            # empty list condition handled with syntax error in calling method
        return False

    def inequality_op(self):
        if (
            (op := self.expect("IS_EQUAL_TO"))
            or (op := self.expect("NEQ"))
            or (op := self.expect("GT"))
            or (op := self.expect("LT"))
            or (op := self.expect("GE"))
            or (op := self.expect("LE"))
        ):
            return op
        return False

    def bracket_expr(self):
        if l_delim := self.l_delimiter():
            expected = "]" if l_delim.value == "[" else ")"
            if expr := self.expr():
                if r_delim := self.r_delimiter():
                    if r_delim.value != expected:
                        SyntaxErr(f"Unmatched delimiter: expected '{expected}'", *self.position).throw()
                    return expr
                SyntaxErr(f"Unmatched delimiter: expected '{expected}'", *self.position).throw()
            SyntaxErr("Expected expression", *self.position).throw()
        return False

    def conditional_goto(self):
        if self.expect("@If"):
            if conditions := self.filters():
                if self.expect("Then"):
                    if headline := self.bracket_expr():
                        return ConditionalGoto(conditions, headline)
                    SyntaxErr("Expected @Goto headline identifier after Then" * self.position).throw()
                SyntaxErr("Expected 'Then' after conditions for @If", *self.position).throw()
            SyntaxErr("Expected conditioanl expression after @If", *self.position).throw()
        return False

    def follow_up(self):
        if call := self.expect("@FollowUp"):
            if l_delim := self.l_delimiter():
                expected = "]" if l_delim.value == "[" else ")"
                if arg0 := self.expect("INTEGER"):
                    if self.expect("COMMA"):
                        if arg1 := self.block():
                            if self.r_delimiter():
                                call.Attach(arg0)
                                call.Attach(arg1)
                                return call
                            SyntaxErr(f"Unmatched delimiter: expected '{expected}'", *self.position).throw()
                        SyntaxErr("Invalid second parameter for @FollowUp", *self.position).throw()
                    SyntaxErr("Expected comma after first parameter for @FollowUp", *self.position).throw()
                ValueErr("First argument to @FollowUp must be an integer", *self.position).throw()
            SyntaxErr("Expected parameter expression after @FollowUp", *self.position).throw()
        return False

    def stmts(self):
        stmts = []
        while True and not self.end_tease:
            if (
                (stmt := self.headline())
                or (stmt := self.follow_up())
                or (stmt := self.expr())
                or (stmt := self.call())
                or (stmt := self.conditional_goto())
            ):
                stmts.append(stmt)
            else:
                break
        if len(stmts) > 0:
            return stmts
            # syntax error here must be handled by calling method because empty stmts is sometimes acceptable
        return False

    def headline(self):
        if self.expect("HEADLINE"):
            return
        return False

    def block_end(self):
        if block_end := self.expect("BLOCK_END"):
            if stmts := self.stmts():
                if self.expect("NEWLINE"):
                    return BlockEnd(block_end, stmts)
            SyntaxErr(f"Expected instruction after {self.last.value} in multiple choice block", *self.position).throw()
        return False

    def l_delimiter(self):
        if (delim := self.expect("[")) or (delim := self.expect("(")):
            return delim
        return False

    def r_delimiter(self):
        if (delim := self.expect(")")) or (delim := self.expect("]")):
            return delim
        return False

    def params(self):
        if l_delim := self.l_delimiter():
            expected = "]" if l_delim.value == "[" else ")"
            exprs = []
            while True and not self.end_tease:
                if expr := self.expr():
                    exprs.append(expr)
                    if self.expect("COMMA"):
                        continue
                    if self.r_delimiter():
                        break
                    else:
                        SyntaxErr(f"Unmatched delimiter, expected {expected}", *self.position).throw()
                break
            if len(exprs) > 0:
                return exprs
                # TODO: handle implicit concat of string expressions?  could just as easily
                #       use an output buffer in the interpreter and not worry about implicit concat
            SyntaxErr("Expected parameter expression", *l_delim.get_position()).throw()
        return False

    def call(self):
        if call := self.expect("FUNCTION_CALL"):
            req_params = DISPATCH_DICT[call.value]["parameters"]
            req = sum([1 for param in req_params if not param["optional"]])
            if params := self.params():
                for i, param in enumerate(params):
                    call.Attach(param, i)
                return call
            else:
                if req > 0:
                    SyntaxErr(f"{call.value} requires parameters", *call.get_position()).throw()
                return call
        return False

    def command_filter_call(self):
        if call := self.expect("COMMAND_FILTER"):
            req_params = DISPATCH_DICT[call.value]["parameters"]
            req = sum([1 for param in req_params if not param["optional"]])
            if params := self.params():
                for i, param in enumerate(params):
                    call.Attach(param, i)
                return call
            else:
                if req > 0:
                    SyntaxErr(f"{call.value} requires parameters", *call.get_position()).throw()
                return call
        return False

    def keyword_call(self):
        if call := self.expect("KEYWORD"):
            req_params = DISPATCH_DICT[call.value]["parameters"]
            req = sum([1 for param in req_params if not param["optional"]])
            if params := self.params():
                for i, param in enumerate(params):
                    call.Attach(param, i)
                return call
            else:
                if req > 0:
                    SyntaxErr(f"{call.value} requires parameters" * call.get_position()).throw()
                return call
        return False

    def ref(self):
        op = self.expect("NOT")
        if not op:
            op = self.expect("MINUS")
        if self.expect("#Var"):
            if l_delim := self.l_delimiter():
                expected = "]" if l_delim.value == "[" else ")"
                if ref_name := self.expr():
                    if self.r_delimiter():
                        if op:
                            return BinaryExpression(None, op, VarRef(ref_name))
                        else:
                            return VarRef(ref_name)
                    SyntaxErr(f"Unmatched delimiter, expected {expected}", *self.position).throw()
                SyntaxErr("Expected string", *self.position).throw()
            SyntaxErr(f"Expected delimiter after {op.value}", *op.get_position()).throw()
        return False

    def string_value(self):
        if (
            (string := self.expect("STRING"))
            or (string := self.expect("VOCAB"))
            or (string := self.ref())
            or (string := self.keyword_call())
        ):
            return string
        return False

    def int_value(self):
        op = self.expect("MINUS")
        int = self.expect("INTEGER")
        if not int:
            int = self.ref()
        if op and int:
            return BinaryExpression(None, op, int)
        elif op and not int:
            SyntaxErr("Expected Integer or variable reference after unary '-' operator", *self.position).throw()
        return int

    def binary_int(self):
        if int := self.int_value():
            if op := self.math_op():
                if int2 := self.int_value():
                    return BinaryExpression(int, op, int2)
                SyntaxErr("Expected expression after operator", *self.position).throw()
        return int

    def binary_string(self):
        if string := self.string_value():
            if op := self.expect("PLUS"):
                if string2 := self.string_value():
                    return BinaryExpression(string, op, string2)
                if binary_int := self.binary_int():
                    return BinaryExpression(string, op, binary_int)
                SyntaxErr("Exected expression", *self.position).throw()
            if op := self.expect("MINUS"):
                if string2 := self.string_value():
                    return BinaryExpression(string, op, string2)
                SyntaxErr("Expected expression", *op.get_position()).throw()
            if op := self.expect("TIMES"):
                if binary_int := self.string_value():
                    return BinaryExpression(string, op, binary_int)
                SyntaxErr("Expected expression", *op.get_position()).throw()
            return string
        mark = self.mark()
        if binary_int := self.binary_int():
            if (op := self.expect("PLUS")) or (op := self.expect("TIMES")):
                if string := self.string_value():
                    return BinaryExpression(binary_int, op, string)
                SyntaxErr("Expected expression", *op.get_position()).throw()
            self.reset(mark)
            return False
        return False

    def math_op(self):
        if (
            (op := self.expect("PLUS"))
            or (op := self.expect("MINUS"))
            or (op := self.expect("TIMES"))
            or (op := self.expect("DIVIDED_BY"))
            or (op := self.expect("EXPONENT"))
            or (op := self.expect("MODULO"))
        ):
            return op

    def assignment(self):
        mark = self.mark()
        if ref := self.ref():
            if (op := self.expect("INC_BY")) or (op := self.expect("DEC_BY")):
                if expr := self.bracket_expr():
                    return BinaryExpression(ref, op, expr)
                SyntaxErr("Expected expression", *self.position).throw()
            elif op := self.expect("EQUALS"):
                if expr := self.bracket_expr():
                    if op2 := self.math_op():
                        if expr2 := self.bracket_expr():
                            return BinaryExpression(ref, op, BinaryExpression(expr, op2, expr2))
                        SyntaxErr("Expected expression", *self.position).throw()
                    return BinaryExpression(ref, op, expr)
                SyntaxErr("Expected expression", *self.position).throw()
            elif (op := self.expect("INC")) or (op := self.expect("DEC")):
                return BinaryExpression(ref, op, None)
            self.reset(mark)  # backtrack if we didn't find an operator
        return False  # NOTE: this must be return False, not return ref

    def expr(self):
        # NOTE: We have to check assignment first, otherwise we could consume a ref and leave
        #       a broken assignment statement in the stream.
        expr = self.assignment()
        if not expr:
            expr = self.binary_string()
        if not expr:
            expr = self.binary_int()
        if not expr:
            expr = self.expect("BOOLEAN")
        if not expr:
            expr = self.bracket_expr()
        return expr

    def conditional(self):
        # conditional = NOT? command_filter_call
        op = self.expect("NOT")
        if condition := self.command_filter_call():
            if op:
                return BinaryExpression(None, op, condition)
            if condition:
                return condition
        if op and not condition:
            SyntaxErr("Expected expression after '!'", *self.position).throw()
        mark = self.mark()
        if expr := self.expr():
            if self.position[0] == 155:
                pass
            if op := self.inequality_op():
                if expr2 := self.expr():
                    return BinaryExpression(expr, op, expr2)
                SyntaxErr("Expected expression after operator", *self.position).throw()
            else:
                self.reset(mark)
        return False  # NOTE: this must be return False, not return expr

    def filters(self):
        # Shunting yard algorithm to convert to reverse polish notation
        # handles implementing precedence of AND/OR operators
        # We also handle the implict AND operator for command filters
        queue = []
        op_stack = []
        last = None
        # TODO : add parentheses support
        while True and not self.end_tease:
            if (filter := self.conditional()) and last is None or last == "op":
                queue.append(filter)
                last = "filter"
            if (filter := self.conditional()) and last == "filter":
                op_stack.append(OperatorToken(*filter.get_position(), "AND"))
                queue.append(filter)
                last = "filter"

            if op := self.expect("AND"):
                op_stack.append(op)
                last = "op"
            elif op := self.expect("OR"):
                if len(op_stack) > 1 and op_stack[-1].value == "AND":
                    queue.append(op_stack.pop())
                    op_stack.append(op)
                    last = "op"
            else:
                break
        while len(op_stack) > 0:
            queue.append(op_stack.pop())
        if len(queue) > 0:
            return queue
        # No syntax error here, empty filters is acceptable.
        return False


def math_op(self):
    if (
        (op := self.expect("PLUS"))
        or (op := self.expect("MINUS"))
        or (op := self.expect("TIMES"))
        or (op := self.expect("DIVIDED_BY"))
        or (op := self.expect("MODULO"))
        or (op := self.expect("EXPONENT"))
    ):
        return op
    return False


if __name__ == "__main__":
    from tokenizer import Tokenizer
    import os

    path = os.path.dirname(__file__)
    path = os.path.join(path, "Main_Start.txt")
    with open(path, "r") as f:
        script = f.read()
    tokenizer = Tokenizer(script, path)
    tokenizer.run()
    parser = Parser(tokenizer.tokens)
    parser.run()
    # for block in parser.blocks:
    # print(block)
