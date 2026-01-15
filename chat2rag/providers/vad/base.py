from abc import ABC, abstractmethod


class VAD(ABC):
    @abstractmethod
    def is_vad(self, data):
        pass

    def reset_states(self):
        pass
