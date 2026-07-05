import logging
import json


class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def info(self, message: str = "", **kwargs):
        # FIX: accepts a positional message string + optional keyword context
        payload = {"message": message, **kwargs}
        self.logger.info(json.dumps(payload))

    def error(self, message: str = "", **kwargs):
        payload = {"message": message, **kwargs}
        self.logger.error(json.dumps(payload))