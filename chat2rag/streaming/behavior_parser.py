import re
from io import StringIO

from chat2rag.streaming.constants import BEHAVIOR_TAG_PATTERN, BEHAVIOR_TAG_TYPES


class BehaviorTagParser:
    def __init__(self, tag_types: tuple = None):
        self.tag_types = tag_types or BEHAVIOR_TAG_TYPES
        self._buffer = StringIO()
        self._accumulated = {tag.lower(): "" for tag in self.tag_types}
        self._tag_pattern = re.compile(
            r"\[(" + "|".join(self.tag_types) + r"):([^\]]+)\]"
        )

    def extract_tags(self, text: str) -> tuple[str, str, dict]:
        combined = self._buffer.getvalue() + text
        self._buffer = StringIO()

        clean_text_builder = StringIO()
        remaining_buffer = StringIO()
        extracted_tags = {tag.lower(): "" for tag in self.tag_types}

        i = 0
        while i < len(combined):
            if combined[i] == "[":
                bracket_start = i
                tag_end = combined.find("]", i)

                if tag_end == -1:
                    remaining_buffer.write(combined[bracket_start:])
                    break

                tag_content = combined[i + 1 : tag_end]

                if ":" in tag_content:
                    tag_type, tag_value = tag_content.split(":", 1)
                    if tag_type in self.tag_types:
                        tag_key = tag_type.lower()
                        if not extracted_tags[tag_key]:
                            extracted_tags[tag_key] = tag_value
                        i = tag_end + 1
                        continue

                clean_text_builder.write(combined[i])
                i += 1
            else:
                clean_text_builder.write(combined[i])
                i += 1

        clean_text = clean_text_builder.getvalue()
        remaining = remaining_buffer.getvalue()

        if any(extracted_tags.values()):
            for key, value in extracted_tags.items():
                if value:
                    self._accumulated[key] = value

        return clean_text, remaining, extracted_tags

    def get_accumulated_tags(self) -> dict:
        return self._accumulated.copy()

    def reset_buffer(self):
        self._buffer = StringIO()

    def reset_accumulated(self):
        self._accumulated = {tag.lower(): "" for tag in self.tag_types}

    @staticmethod
    def clean_behavior_tags(text: str) -> str:
        return BEHAVIOR_TAG_PATTERN.sub("", text).strip()
