from abc import ABC, abstractmethod

from pydantic import BaseModel


class Output(BaseModel, ABC):
    type: str

    @abstractmethod
    def process(self, text: str) -> str: ...
