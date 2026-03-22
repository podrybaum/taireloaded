
events = {}

class Bus:
    @staticmethod
    def register(event, handler=None):
        if event not in events:
            events[event] = []
        if handler:
            events[event].append(handler)

    @staticmethod
    def sub(event, handler):
        if event in events:
            events[event].append(handler)

    @staticmethod
    def emit(event, *args, **kwargs):
        if event in events:
            for handler in events[event]:
                handler(*args, **kwargs)

    @staticmethod
    def unsub(event, handler):
        if event in events:
            events[event].remove(handler)

