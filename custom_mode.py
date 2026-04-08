from bus import Bus
from message_classes import UserMessage


class CustomMode:
    def __init__(self, runtime, mode, headline, triggers):
        self.runtime = runtime
        self.triggers = triggers
        self.mode = mode
        self.headline = headline
        Bus.sub("new_message", self._on_new_message)
        Bus.sub("clear_modes", lambda *args: self.__del__())

    def _on_new_message(self, sender, message):
        if isinstance(message, UserMessage):
            for trigger in self.triggers:
                if trigger in message.text:
                    self.runtime.goto(self.headline)
                    del self

    def __del__(self):
        Bus.unsub("new_message", self._on_new_message)
