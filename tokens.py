import os
import random
from abc import abstractmethod, ABC

from dispatch_dict import DISPATCH_DICT
from tai_exceptions import NotImplementedErr, SyntaxErr, TypeErr, RuntimeErr
from utils import is_valid_filename

APPLICATION_ROOT = os.path.dirname(os.path.abspath(__file__))

class Token(ABC):
    def __init__(self, line, pos, path, value):
        self.line = line
        self.pos = pos
        self.path = path
        self.value = value
        self.ttype = None

    @abstractmethod
    def __repr__(self):
        raise NotImplementedError
    
    @abstractmethod
    def Accept(self, other):
        raise NotImplementedError

    def get_position(self):
        return (self.line, self.pos, self.path)


class Evaluable(ABC):
    @abstractmethod
    def Evaluate(self):
        raise NotImplementedError

    @abstractmethod
    def Bool(self):
        raise NotImplementedError


class Parameterized:
    def __init__(self):
        self.params = []

    def Attach(self, param, position):
        """
        Attach a parameter at a given position in the parameter list.

        Parameters
        ----------
        param : Any
            The parameter to attach.
        position : int
            The position to attach the parameter at.

        Returns
        -------
        None
        """
        while len(self.params) <= position:
            self.params.append(None)
        self.params[position] = param


class LiteralToken(Token):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        if value == "\n":
            self.ttype = "NEWLINE"
        if value == "[":
            self.ttype = "LBRACKET"
        if value == "(":
            self.ttype = "LPAREN"
        if value == ")":
            self.ttype = "RPAREN"
        if value == "]":
            self.ttype = "RBRACKET"
        if value == ",":
            self.ttype = "COMMA"

    def Accept(self, other):
        return other.VisitLiteralToken(self)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f"LiteralToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.ttype})"


class IntegerToken(Token, Evaluable):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        self.ttype = "INTEGER"

    def Accept(self, other):
        return other.VisitIntegerToken(self)

    def Evaluate(self):
        return int(self.value)

    def __repr__(self):
        return f"IntegerToken(Line: {self.line}, Columnn: {self.pos}, File: {self.path}, {self.value})"

    def Bool(self):
        return self.value != 0


class StringToken(Token, Evaluable):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        self.ttype = "STRING"

    def Accept(self, other):
        return other.VisistStringToken(self)

    def Evaluate(self):
        return self.value

    def __repr__(self):
        return f"StringToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.value})"

    def Bool(self):
        return self.value != ""


class OperatorToken(Token):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        match value:
            case "&&":
                self.ttype = "AND"
            case "||":
                self.ttype = "OR"
            case "+":
                self.ttype = "PLUS"
            case "-":
                self.ttype = "MINUS"
            case "*":
                self.ttype = "TIMES"
            case "/":
                self.ttype = "DIVIDED_BY"
            case "^":
                self.ttype = "EXPONENT"
            case "%":
                self.ttype = "MODULO"
            case "==":
                self.ttype = "IS_EQUAL_TO"
            case ">":
                self.ttype = "GT"
            case "<":
                self.ttype = "LT"
            case ">=":
                self.ttype = "GE"
            case "<=":
                self.ttype = "LE"
            case "!=":
                self.ttype = "NEQ"
            case "+=":
                self.ttype = "INC_BY"
            case "-=":
                self.ttype = "DEC_BY"
            case "=":
                self.ttype = "EQUALS"
            case "Then":
                self.ttype = "THEN"
            case _:
                self.ttype = value

    def Accept(self, visitor):
        return visitor.VisitOperatorToken(self)

    def __repr__(self):
        return f"OperatorToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.ttype})"

    def Execute(self, left: Evaluable, right: Evaluable):
        left_token = left
        left = left.Evaluate()
        right = right.Evaluate()
        match self.ttype:
            case "PLUS":  # Python's + operator already works the way we want ours to work
                return left + right
            case "MINUS":
                if int(left) and int(right):
                    return int(left) - int(right)
                if isinstance(left, str) and isinstance(right, str):
                    return left.replace(right, "")
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "*":
                if isinstance(left, int) and isinstance(right, int):
                    return int(left) * int(right)
                if isinstance(left, str) and isinstance(right, int):
                    ret_value = ""
                    for i in range(right):
                        ret_value += left
                    return ret_value
                if isinstance(left, int) and isinstance(right, str):
                    ret_value = ""
                    for i in range(left):
                        ret_value += right
                    return ret_value
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "/":
                if isinstance(left, int) and isinstance(right, int):
                    if left % right == 0:
                        return left / right
                    else:
                        TypeErr(
                            "Division results in floating point value, not currently supported.",
                            *self.get_position()
                        ).throw()
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "^":
                if isinstance(left, int) and isinstance(right, int):
                    return left**right
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "%":
                if isinstance(left, int) and isinstance(right, int):
                    return left % right
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "==":
                return left == right
            case ">":
                if isinstance(left, int) and isinstance(right, int):
                    return left > right
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "<":
                if isinstance(left, int) and isinstance(right, int):
                    return left < right
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "AND":
                return left.Bool() and right.Bool()
            case "OR":
                return left.Bool() and right.Bool()
            case ">=":
                if isinstance(left, int) and isinstance(right, int):
                    return left >= right
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "<=":
                if isinstance(left, int) and isinstance(right, int):
                    return left <= right
                else:
                    NotImplementedErr(
                        f"Operation not implemented for types {type(left)} and {type(right)}.",
                        *self.get_position()
                    ).throw()
            case "!=":
                return left != right
            case "+=":
                if not isinstance(VarRef, left_token):
                    SyntaxErr("Not a valid target for assignment.", self.line, self.pos, self.path).throw()
                else:
                    # TODO increment variable value
                    pass
            case "-=":
                if not isinstance(VarRef, left_token):
                    SyntaxErr("Not a valid target for assignment.", self.line, self.pos, self.path).throw()
                else:
                    # TODO: decrement variable value
                    pass
            case _:
                NotImplementedErr("Operation not implemented.", self.line, self.pos, self.path).throw()


class UnaryOperatorToken(Token):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        match value:
            case "++":
                self.ttype = "INC"
            case "--":
                self.ttype = "DEC"
            case "-":
                self.ttype = "NEG"
            case "!":
                self.ttype = "NOT"
            case _:
                self.ttype = value

    def Accept(self, other):
        return other.VisitUnaryOperatorToken(self)

    def __repr__(self):
        return f"UnaryOperatorToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.ttype})"

    def Execute(self, operand):
        op_value = operand.Evaluate()
        match self.value:
            case "INC":
                if not isinstance(VarRef, operand):
                    SyntaxErr("Not a valid target for assignment.", self.line, self.pos, self.path).throw()
                else:
                    # TODO: Increment variable value by 1
                    pass
            case "DEC":
                if not isinstance(VarRef, operand):
                    SyntaxErr("Not a valid target for assignment.", self.line, self.pos, self.path).throw()
                else:
                    # TODO: Decrement variable value by 1
                    pass
            case "NEG":
                if isinstance(int, op_value):
                    return -op_value
                else:
                    NotImplementedErr(
                        f"Type{type(op_value)} not supported for negation.", self.line, self.pos, self.path
                    ).throw()
            case "NOT":
                if isinstance(bool, op_value):
                    return not op_value
                else:
                    NotImplementedErr(
                        f"Type{type(op_value)} not supported for logical negation.", self.line, self.pos, self.path
                    ).throw()
            case _:
                NotImplementedErr("Operation not implemented.", self.line, self.pos, self.path).throw()


class HeadlineToken(Token):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        self.ttype = "HEADLINE"

    def Accept(self, other):
        return other.VisitHeadlineToken(self)

    def __repr__(self):
        return f"HeadlineToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.value})"


class FunctionCall(Token, Parameterized):
    def __init__(self, line, pos, path, value):
        Parameterized.__init__(self)
        super().__init__(line, pos, path, value)
        if value in ["@DifferentAnswer", "@AcceptAnswer"]:
            self.ttype = "BLOCK_END"
        else:
            self.ttype = "FUNCTION_CALL"

    def Accept(self, visitor):
        return visitor.VisitFunctionCall(self)

    def __repr__(self):
        return f"FunctionCall(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.value})"

    def Execute(self):
        return DISPATCH_DICT[self.value]["implemented_by"]


class BooleanToken(Token, Evaluable):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        self.ttype = "BOOLEAN"

    def Accept(self, other):
        return other.VisitBooleanToken(self)

    def Evaluate(self):
        if self.value.lower() == "true":
            return True
        if self.value.lower() == "false":
            return False
        else:
            TypeErr(f"Invalid type, expected boolean, got {type(self.value)}.", self.line, self.pos, self.path).throw()

    def __repr__(self):
        return f"BooleanToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.value})"

    def Bool(self):
        return self.Evaluate()


class KeywordToken(Token, Parameterized):
    def __init__(self, line, pos, path, value):
        Parameterized.__init__(self)
        super().__init__(line, pos, path, value)
        if value == "#VAR":
            self.ttype = "#VAR"
        else:
            self.ttype = "KEYWORD"
    
    def Accept(self, other):
        return other.VisitKeywordToken(self)

    def Evaluate(self):
        return DISPATCH_DICT[self.value]["implemented_by"](self.params)

    def __repr__(self):
        return f"KeywordToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.value})"

    def Bool(self):
        return self.Evaluate() != ""


class VocabToken(Token, Evaluable):
    def __init__(self, line, pos, path, value):
        super().__init__(line, pos, path, value)
        self.ttype = "VOCAB"
        self.filename = f"{value}.txt"
        personality_dict = {"personality":""}
        Bus.emit("get_current_personality", personality_dict)
        self.filepath = os.path.join(APPLICATION_ROOT, "Scripts", personality_dict["personality"], "Vocabulary", self.filename)

    def __repr__(self):
        return f"VocabToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.value})"

    def Bool(self):
        return self.Evaluate() != ""

    def Accept(self, other):
        return other.VisitVocabToken(self)

    def Evaluate(self):
        line, lineNo = self.get_line()
        # subtokenizer = Tokenizer(line, self.filepath, line, 1)
        # subtokenizer.run()
        # TODO: Pass this token stream to the parser and then return any result
        #       If the line we pass is filtered, fetch another line until we succeed
        #       It's possible for a vocab token to return the empty string after processing.
        return ""

    def get_line(self):
        if not os.path.isfile(self.filepath):
            return (f"MISSING_VOCAB_FILE: {self.filename}", 0)
        with open(self.filepath, "r") as f:
            lines = f.readlines()
            if len(lines == 0):
                return (f"EMPTY_VOCAB_FILE: {self.filename}", 0)

            index = random.randint(0, len(lines) - 1)
            return (lines[index], index + 1)


class CommandFilterToken(Token, Parameterized):
    def __init__(self, line, pos, path, value):
        Parameterized.__init__(self)
        super().__init__(line, pos, path, value)
        self.ttype = "COMMAND_FILTER"

    def Accept(self, other):
        return other.VisitCommandFilter(self)
   
    def __repr__(self):
        return f"CommandFilterToken(Line: {self.line}, Column: {self.pos}, File: {self.path}, {self.value})"


class VarRef(Evaluable):
    def __init__(self, expr):
        Evaluable.__init__(self)
        self.expr = expr
        self.filename = f"{self.expr.Evaluate()}"
        if not is_valid_filename(self.filename):
            RuntimeErr("Variable names must be valid Windows filenames.", *self.expr.get_position()).throw()
        self.filepath = ""

    def get_position(self):
        return self.expr.get_position()

    def Accept(self, other):
        self.filepath = os.path.join(other.var_path, self.filename)
        return other.VisitVarRef(self)

    def Evaluate(self):
        if not os.path.isfile(self.filepath):
            return f"MISSING_VARIABLE_FILE: {self.filename}"
        with open(self.filepath, "r") as f:
            value = f.read()
            if value == "":
                return f"CORRUPTED_VARIABLE_FILE: {self.filename}"
            if int(value):
                return int(value)
            if bool(value):
                return bool(value)
            else:
                return value

    def assign(self, value):
        with open(self.filepath, "w") as f:
            f.write(value)

    def Bool(self):
        value = self.Evaluate()
        try:
            int(value)
            return int(value) != 0
        except ValueError:
            if value == "True":
                return True
            if value == "False":
                return False
            else:
                return value != ""

    def __repr__(self):
        return f"VarRef({self.expr})"
