from enum import Enum


class ProcessType(str, Enum):
    BATCH = "batch"
    STREAM = "stream"
