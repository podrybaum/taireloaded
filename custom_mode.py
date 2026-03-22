from bus import Bus
from message_classes import UserMessage
from tokens import HeadlineToken


class CustomMode:
    def __init__(self, runtime, mode, headline_token: HeadlineToken, triggers):
        self.triggers = triggers
        self.mode = mode
        self.runtime = runtime
        self.headline = headline_token
        Bus.sub("new_message", self._on_new_message)

    def _on_new_message(self, sender, message):
        if isinstance(message, UserMessage):
            for trigger in self.triggers:
                if trigger in message.text:
                    self.resolve()

    def resolve(self):
        self.runtime.goto(self.headline)

    def __del__(self):
        Bus.unsub("new_message", self._on_new_message)
