from abc import ABC
from abc import abstractmethod

from pydantic import BaseModel


class Output(BaseModel, ABC):
    type: str

    @abstractmethod
    def process(self, text: str):
        pass
