from abc import ABC, abstractmethod
from dataclasses import replace

from haystack.dataclasses import StreamingChunk


class StreamModeProcessor(ABC):
    @abstractmethod
    def process_chunk(self, chunk: StreamingChunk) -> tuple[bool, list[StreamingChunk]]:
        pass

    @abstractmethod
    def finalize(self) -> list[StreamingChunk]:
        pass

    @abstractmethod
    def reset(self):
        pass


class StreamProcessor(StreamModeProcessor):
    def __init__(self):
        pass

    def process_chunk(self, chunk: StreamingChunk) -> tuple[bool, list[StreamingChunk]]:
        if chunk.content:
            return True, [chunk]
        return False, []

    def finalize(self) -> list[StreamingChunk]:
        return []

    def reset(self):
        pass


class BatchProcessor(StreamModeProcessor):
    def __init__(self, split_symbols: list[str]):
        self.split_symbols = split_symbols
        self._batch: list[StreamingChunk] = []

    def process_chunk(self, chunk: StreamingChunk) -> tuple[bool, list[StreamingChunk]]:
        if not chunk.content:
            return False, []

        content = chunk.content
        last_split_pos = 0
        output_chunks = []

        for i, char in enumerate(content):
            if char in self.split_symbols:
                split_chunk = replace(chunk, content=content[last_split_pos : i + 1])
                self._batch.append(split_chunk)

                batch_content = "".join([c.content for c in self._batch])
                merged_chunk = replace(chunk, content=batch_content)
                output_chunks.append(merged_chunk)

                self._batch.clear()
                last_split_pos = i + 1

        if last_split_pos < len(content):
            remaining_chunk = replace(chunk, content=content[last_split_pos:])
            self._batch.append(remaining_chunk)

        if output_chunks:
            return True, output_chunks

        return False, []

    def finalize(self) -> list[StreamingChunk]:
        if self._batch:
            batch_content = "".join([c.content for c in self._batch])
            if batch_content.strip():
                merged_chunk = replace(self._batch[-1], content=batch_content)
                self._batch.clear()
                return [merged_chunk]
        return []

    def reset(self):
        self._batch.clear()

    def get_current_batch_content(self) -> str:
        return "".join([c.content for c in self._batch])


def create_mode_processor(
    is_batch: bool, split_symbols: list[str] = None
) -> StreamModeProcessor:
    if is_batch:
        default_symbols = ["，", "；", "。", "：", "？", "！", "\n", ",", ";", "?", "!"]
        symbols = split_symbols or default_symbols
        return BatchProcessor(symbols)
    else:
        return StreamProcessor()
