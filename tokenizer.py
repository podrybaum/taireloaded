# Tokenizer.py
#
# Performs lexical analysis of a script file, translating into a token stream that can
# be consumed by the parser to produce an Abstract Syntax Tree, which can be consumed by the interpreter
# to execute a script.

# TODO: We have to special case @PlayVideo because it can currently accept
#       params in either brackets or parens and they mean different things.

import os
import re
from bus import Bus
from tokens import (
    BooleanToken,
    OperatorToken,
    UnaryOperatorToken,
    HeadlineToken,
    IntegerToken,
    StringToken,
    FunctionCall,
    KeywordToken,
    CommandFilterToken,
    VocabToken,
    LiteralToken,
    Parameterized,
)
from tai_exceptions import SyntaxErr
from dispatch_dict import DISPATCH_DICT
APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))
# For command names where we extract a parameter from the name itself,
# this maps what position to attach the parameter in, the default is 0
PENDING_PARAMS_POS = {"@FollowUp": 1, "@Random": 2}


class Lexer:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def peek(self):
        if self.tokenizer.pos + 1 >= len(self.tokenizer.input):
            return -1
        return self.tokenizer.input[self.tokenizer.pos + 1]

    def read(self):
        self.tokenizer.pos += 1
        self.tokenizer.line_pos += 1
        return self.tokenizer.input[self.tokenizer.pos]

    def discard(self):
        self.tokenizer.line_pos += 1
        self.tokenizer.token_start += 1
        self.tokenizer.pos += 1


class Buffer:
    def __init__(self, tokenizer):
        self.string = ""
        self.tokenizer = tokenizer

    def write(self, text):
        self.string += text

    def clear(self):
        self.string = ""
        self.tokenizer.token_start = self.tokenizer.line_pos + 1


class Tokenizer:
    def __init__(self, input, path, line=1, line_pos=1):
        self.input = input
        self.path = path
        self.line = line
        self.pos = -1
        self.line_pos = line_pos
        self.lexer = Lexer(self)
        self.tokens = []
        self.LexerMode = "string"
        self.switches = ["@", "#", "[", "(", "\n", ")", "]"]
        self.token_buffer = Buffer(self)
        self.token_start = self.line_pos
        self.expected = []
        self.params_return = False
        self.equals_context = "="
        self.pending_param = None
        self.end_tease = False
        Bus.sub("end_tease", lambda: setattr(self, "end_tease", True))
        self.operators = ["+", "-", "*", "/", "^", "%", "=", ">", "<", "A", "O", "&", "!", "|", "T"]

    def advance(self):
        if self.lexer.peek() == -1:
            return
        self.token_buffer.string += self.lexer.read()
        return

    def consume_until(self, char):
        while self.lexer.peek() != char:
            self.advance()
            if self.lexer.peek() == -1:
                SyntaxErr(f"EOL encountered while expecting {char}.", self.line, self.pos, self.path).throw()
                return
        return self.lexer.peek() == char

    def handle_deprecated_token(self):
        token_str = DISPATCH_DICT[self.token_buffer.string]["deprecated_by"]
        subtokenizer = Tokenizer(token_str, self.path, self.line, self.token_start)
        subtokenizer.run()
        self.tokens.extend(subtokenizer.tokens)
        self.token_buffer.clear()

    def handle_pending_param(self):
        if self.tokens[-1].value is PENDING_PARAMS_POS:
            pos = PENDING_PARAMS_POS[self.tokens[-1].value]
        else:
            pos = 0
        if isinstance(self.tokens[-2], Parameterized):
            tok_type = IntegerToken if int(self.pending_param) else StringToken
            self.tokens[-2].Attach(tok_type(self.line, self.pos, self.path, self.pending_param), pos)
            self.pending_param = None
        else:
            # this is a developer fuck-up so we raise here and not throw
            raise TypeError(
                f"Attempting to attach parameter to non-parameterized token, at line: {self.line}, column: {self.pos}"
            )

    def emit(self, type: type):
        if self.token_buffer.string == "" or self.token_buffer.string is None:
            return
        if type == StringToken and self.token_buffer.string in ["True", "False"]:
            type = BooleanToken
        if self.token_buffer.string in DISPATCH_DICT.keys():
            if DISPATCH_DICT[self.token_buffer.string]["deprecated_by"] != "":
                return self.handle_deprecated_token()
        if self.token_buffer.string == "=":
            self.token_buffer.string = self.equals_context
        self.tokens.append(type(self.line, self.token_start, self.path, self.token_buffer.string))
        if self.params_return:
            self.LexerMode = "params"
        if self.pending_param is not None:
            self.handle_pending_param()
        self.token_buffer.clear()

    def switch_mode(self):
        if self.lexer.peek() == "(" and self.line_pos == 1:
            self.LexerMode = "headline"
            return
        match self.lexer.peek():
            case "@":
                self.LexerMode = "command"
            case "#":
                self.LexerMode = "keyword"
            case "(" | "[" | ")" | "]":
                self.LexerMode = "params"
            case _:
                self.LexerMode = "string"

        if self.LexerMode == "string":
            self.switches = ["@", "#", "[", "(", "\n", ")", "]"]
            if self.params_return:
                self.switches.append(",")
        elif self.LexerMode == "command" or self.LexerMode == "keyword":
            self.switches = ["[", " ", "(", "\n", ")", "]", ","]

    def expect_string(self, expected):
        remaining = self.input[self.pos + 1 :]
        if remaining.startswith(expected):
            for _ in range(len(expected)):
                self.advance()
            return True
        return False

    def empty_buffer(self):
        return self.token_buffer.string == "" or self.token_buffer.string is None

    def match_with_wildcard(self, string):
        if string in DISPATCH_DICT.keys():
            return False
        for key in DISPATCH_DICT.keys():
            if "$" in key:
                pattern = key.replace("$", "(\\w+)")
                match = re.match(pattern, string)
                if match:
                    self.token_buffer.string = key
                    self.handle_deprecated_token()
                    self.pending_param = match.group(1)
                    return True

    def run(self):
        self.switch_mode()  # set the LexerMode at the beginning of the input.
        while self.lexer.peek() != -1 and not self.end_tease:
            if self.lexer.peek() in self.operators:
                self.tokenize_operators()
            if self.lexer.peek() == "," and self.params_return and self.empty_buffer():
                self.advance()
                self.emit(LiteralToken)
            if self.lexer.peek() == "\n":
                self.advance()
                self.emit(LiteralToken)
                self.line_pos = 1
                self.token_start = 1
                self.line += 1
            # Any time the token buffer is empty, whitespace is insignificant
            if self.empty_buffer():
                while self.lexer.peek() == " ":
                    self.lexer.discard()
            # handle position data on newlines
            while self.LexerMode == "headline":
                if self.lexer.peek() == "(":
                    self.lexer.discard()
                    self.consume_until(")")
                    self.token_start -= 1  # after discarding the LPAREN, token_start is off by 1 "technically"
                    self.emit(HeadlineToken)
                    self.lexer.discard()
                    self.consume_until("\n")
                    if len(self.token_buffer.string) > 0 and not all(
                        self.token_buffer.string[i] == " " for i in range(len(self.token_buffer.string))
                    ):
                        SyntaxErr("Unexpected input after @Goto headline", self.line, self.pos, self.path).throw()
                    self.token_buffer.clear()
                    break
            while self.LexerMode in ["string", "command", "keyword"] and self.lexer.peek() != -1:
                while self.lexer.peek() not in self.switches:
                    self.advance()
                    if (self.lexer.peek() == -1 or self.lexer.peek() in self.switches) and not self.empty_buffer():
                        if self.LexerMode == "string":
                            if (
                                self.lexer.peek() in ["[", "(", ")", "]"]
                                and self.line_pos > 1
                                and not self.params_return
                            ):
                                self.advance()
                            if self.params_return:
                                try:
                                    int(self.token_buffer.string)
                                    self.emit(IntegerToken)
                                    break
                                except ValueError:
                                    pass
                                self.emit(StringToken)
                                break
                            if self.lexer.peek() in self.switches:
                                self.emit(StringToken)
                        if self.LexerMode == "command":
                            if (
                                self.handle_comment()
                                or self.handle_equals_context()
                                or self.handle_miniscript()
                                or self.handle_round_var()
                            ):
                                break
                            else:
                                if not self.match_with_wildcard(self.token_buffer.string):
                                    if DISPATCH_DICT[self.token_buffer.string]["category"] == "Command":
                                        self.emit(FunctionCall)
                                    else:
                                        self.emit(CommandFilterToken)
                                    break
                                else:
                                    break
                        if self.LexerMode == "keyword":
                            if self.token_buffer.string in DISPATCH_DICT.keys():
                                self.emit(KeywordToken)
                            else:
                                self.emit(VocabToken)
                            break
                break
            while self.LexerMode == "params":
                if self.lexer.peek() == "[":
                    self.expected.insert(0, "]")
                    self.advance()
                    self.emit(LiteralToken)
                    self.params_return = True
                elif self.lexer.peek() == "(":
                    self.expected.insert(0, ")")
                    self.advance()
                    self.emit(LiteralToken)
                    self.params_return = True
                elif self.lexer.peek() == self.expected[0] and self.empty_buffer():
                    self.expected.pop(0)
                    self.advance()
                    self.emit(LiteralToken)
                    self.params_return = False
                    if len(self.expected) == 0:
                        self.handle_PlayAudioLoop()
                        break
                if self.lexer.peek() == "\n" and len(self.expected) > 0:
                    SyntaxErr(
                        f"Unmatched delimiter, EOL encountered while expecting {self.expected[0]}",
                        self.line,
                        self.line_pos,
                        self.path,
                    ).throw()
                if self.lexer.peek() == "," or self.lexer.peek() == self.expected[0] and not self.empty_buffer():
                    self.params_return = True
                match self.lexer.peek():
                    case "@":
                        self.LexerMode = "command"
                    case "#":
                        self.LexerMode = "keyword"
                    case _:
                        self.LexerMode = "string"

                break

            if self.lexer.peek() == -1:
                return
            self.switch_mode()

    def handle_equals_context(self):
        if self.token_buffer.string not in ["@SetVar", "@ChangeVar", "@Variable", "@If"]:
            return False
        if self.token_buffer.string in ["@SetVar", "@ChangeVar"]:
            self.equals_context = "="
        elif self.token_buffer.string == "@Variable":
            self.equals_context = "=="
        elif self.token_buffer.string == "@If":
            self.equals_context = "=="
            self.emit(FunctionCall)
            return True
        self.token_buffer.string = "#Var"
        self.emit(KeywordToken)
        return True

    def tokenize_operators(self):
        while self.lexer.peek() in self.operators or self.lexer.peek() == " ":
            if self.lexer.peek() == "A":
                if self.expect_string("AND"):
                    self.emit(OperatorToken)
                    break
                else:
                    break  # if we got here it's new string data
            if self.lexer.peek() == "O":
                if self.expect_string("OR"):
                    self.emit(OperatorToken)
                    break
                else:
                    break  # if we got here it's new string data
            if self.lexer.peek() == "T":
                if self.expect_string("Then"):
                    self.emit(OperatorToken)
                    break
                else:
                    break  # if we got here it's new string data
            self.advance()
        if len(self.token_buffer.string) > 0 and all(
            self.token_buffer.string[i] == " " for i in range(len(self.token_buffer.string))
        ):
            self.token_buffer.clear()
        else:
            if self.token_buffer.string in ["!", "++", "--", "-"]:
                if self.token_buffer.string == "-" and not int(self.lexer.peek()) and self.lexer.peek() != "#":
                    self.emit(OperatorToken)
                else:
                    self.emit(UnaryOperatorToken)
            else:
                self.emit(OperatorToken)
            self.token_buffer.clear()
        return

    def handle_PlayAudioLoop(self):
        if self.tokens[-1].value != "@PlayAudioLoop":
            return False
        if self.expect_string(" @AudioLoopPause("):
            self.consume_until(")")
            self.tokens[-1].Attach(self.token_buffer.string, 1)
            self.lexer.discard()
            self.token_buffer.clear()

    def consume_bracket_expression(self):
        """Consumes a bracketed (parens or square brackets) expression completely.
        The brackets are discarded and the expression is left sitting in self.token_buffer.string"""
        if self.lexer.peek() in ["(", "["]:
            self.lexer.discard()
            closed = self.consume_until(")")
            if not closed:
                closed = self.consume_until("]")
            if not closed:
                SyntaxErr("Unmatched delimiter, '[' or '(' was unclosed.", self.line, self.line_pos, self.path).throw()
            self.lexer.discard()

    def handle_round_var(self):
        if self.token_buffer.string != "@RoundVar":
            return False
        self.emit(FunctionCall)
        self.consume_bracket_expression()
        self.tokens[-1].Attach(self.token_buffer.string, 0)
        self.token_buffer.clear()
        if self.lexer.peek() == "=":
            self.lexer.discard()
        else:
            SyntaxErr("Expected '=' after @RoundVar parameter", self.line, self.line_pos, self.path).throw()
        self.consume_bracket_expression()
        self.tokens[-1].Attach(self.token_buffer.string, 1)
        self.token_buffer.clear()
        return True

    def handle_comment(self):
        if self.token_buffer.string == "@Info":
            while self.lexer.peek() != "\n":
                self.lexer.discard()
            self.token_buffer.clear()
            return True
        return False

    def handle_miniscript(self):
        cmd_name = self.token_buffer.string
        if cmd_name not in ["@Insert", "@MiniScript"]:
            return False
        # TODO: Handle wildcards
        personality_dict = {"personality":""}
        Bus.emit("get_current_personality", personality_dict)
        path = os.path.join(APPLICATION_ROOT, "Scripts", personality_dict["personality"])
        if cmd_name == "@MiniScript":
            path = os.path.join(path, "Custom", "Miniscripts")
        elif cmd_name == "@Insert":
            path = os.path.join(path, "Insert")
        self.token_buffer.string = "@CallReturn"
        self.emit("FunctionCall")
        self.consume_bracket_expression()
        filename = self.token_buffer.string + ".txt"
        self.token_buffer.clear()
        path = os.path.join(path, filename)
        self.tokens[-1].Attach(StringToken(self.line, self.line_pos, self.path, path), 0)
        return True


if __name__ == "__main__":
    path = os.path.dirname(__file__)
    path = os.path.join(path, "Main_Start.txt")
    with open(path, "r") as f:
        script = f.read()
    tokenizer = Tokenizer(script, path)
    tokenizer.run()
    with open("tokenizer_output.txt", "w") as f:
        for token in tokenizer.tokens:
            f.write(str(token))
            f.write("\n")
