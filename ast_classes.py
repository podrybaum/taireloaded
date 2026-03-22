from tokens import Evaluable

class BinaryExpression(Evaluable):
    def __init__(self, left: Evaluable = None, operator=None, right: Evaluable = None):
        self.left = left
        self.operator = operator
        self.right = right

    def Accept(self, other):
        return other.VisitBinaryExpression(self)

    def Evaluate(self):
        return self.operator.Execute(self.left, self.right)

    def __repr__(self):
        return f"BinaryExpression({self.left}, {self.operator}, {self.right})"

    def get_position(self):
        if self.left is not None:
            return self.left.get_position()
        elif self.op is not None:
            return self.op.get_position()

    def Bool(self):
        return bool(self.Evaluate())


class FilterLine():
    def __init__(self, filters, stmts):
        self.filters = filters
        self.stmts = stmts

    def get_position(self):
        if len(self.filters) > 0:
            return self.filters[0].get_position()
        return self.stmts[0].get_position()

    def Accept(self, other):
        return other.VisitFilterLine(self)

    def __repr__(self):
        return f"FilterLine(Filters: {self.filters}, Stmts: {self.stmts})"


class BlockEnd:
    def __init__(self, block_end, stmts):
        self.block_end = block_end
        self.stmts = stmts

    def get_position(self):
        return self.block_end.get_position()


class ResponseLine:
    def __init__(self, responses, stmts):
        self.responses = responses
        self.stmts = stmts

    def get_position(self):
        return self.responses[0].get_position()


class MultipleChoiceBlock():
    def __init__(self, question, responselines, block_end=None):
        self.question = question
        self.responselines = responselines
        self.block_end = block_end

    def get_position(self):
        return self.question.get_position()

    def Accept(self, other):
        other.VisitMultipleChoiceBlock(self)


class ConditionalGoto():
    def __init__(self, conditions, headline):
        self.conditions = conditions
        self.headline = headline

    def get_position(self):
        return self.conditions[0].get_position()

    def Accept(self, other):
        return self.Execute(other)

    def Execute(self, other):
        for condition in self.conditions:
            if not condition.Evaluate():
                return False
        return other.goto(self.headline)
