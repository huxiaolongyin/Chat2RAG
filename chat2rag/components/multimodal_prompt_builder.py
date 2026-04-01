from dataclasses import replace
from typing import Any, Literal

from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import ChatMessage, ChatRole, TextContent
from haystack.utils import Jinja2TimeExtension
from haystack.utils.jinja2_chat_extension import ChatMessageExtension, templatize_part
from haystack.utils.jinja2_extensions import _extract_template_variables_and_assignments
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

NO_TEXT_ERROR_MESSAGE = "ChatMessages from {role} role must contain text. Received ChatMessage with no text: {message}"
FILTER_NOT_ALLOWED_ERROR_MESSAGE = (
    "The templatize_part filter cannot be used with a template containing a list of"
    "ChatMessage objects. Use a string template or remove the templatize_part filter "
    "from the template."
)


@component
class MultimodalChatPromptBuilder:
    def __init__(
        self,
        template: list[ChatMessage] | str | None = None,
        required_variables: list[str] | Literal["*"] | None = None,
        variables: list[str] | None = None,
    ):
        self._variables = variables
        self._required_variables = required_variables
        self.template = template

        self._env = SandboxedEnvironment(extensions=[ChatMessageExtension])
        self._env.filters["templatize_part"] = templatize_part
        try:
            import arrow

            self._env.add_extension(Jinja2TimeExtension)
        except ImportError:
            pass

        extracted_variables = []
        if template and not variables:
            if isinstance(template, list):
                for message in template:
                    if message.is_from(ChatRole.USER) or message.is_from(
                        ChatRole.SYSTEM
                    ):
                        if message.text is None:
                            raise ValueError(
                                NO_TEXT_ERROR_MESSAGE.format(
                                    role=message.role.value, message=message
                                )
                            )
                        if message.text and "templatize_part" in message.text:
                            raise ValueError(FILTER_NOT_ALLOWED_ERROR_MESSAGE)
                        assigned_variables, template_variables = (
                            _extract_template_variables_and_assignments(
                                env=self._env, template=message.text
                            )
                        )
                        extracted_variables += list(
                            template_variables - assigned_variables
                        )
            elif isinstance(template, str):
                assigned_variables, template_variables = (
                    _extract_template_variables_and_assignments(
                        env=self._env, template=template
                    )
                )
                extracted_variables = list(template_variables - assigned_variables)

        extracted_variables = extracted_variables or []
        self.variables = variables or extracted_variables
        self.required_variables = required_variables or []

        if len(self.variables) > 0 and required_variables is None:
            logger.warning(
                "MultimodalChatPromptBuilder has {length} prompt variables, but `required_variables` is not set. "
                "By default, all prompt variables are treated as optional, which may lead to unintended behavior in "
                "multi-branch pipelines. To avoid unexpected execution, ensure that variables intended to be required "
                "are explicitly set in `required_variables`.",
                length=len(self.variables),
            )

        for var in self.variables:
            if self.required_variables == "*" or var in self.required_variables:
                component.set_input_type(self, var, Any)
            else:
                component.set_input_type(self, var, Any, "")

    @component.output_types(prompt=list[ChatMessage])
    def run(
        self,
        template: list[ChatMessage] | str | None = None,
        template_variables: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, list[ChatMessage]]:
        kwargs = kwargs or {}
        template_variables = template_variables or {}
        template_variables_combined = {**kwargs, **template_variables}

        if template is None:
            template = self.template

        if not template:
            raise ValueError(
                f"The {self.__class__.__name__} requires a non-empty list of ChatMessage instances. "
                f"Please provide a valid list of ChatMessage instances to render the prompt."
            )

        if isinstance(template, list) and not all(
            isinstance(message, ChatMessage) for message in template
        ):
            raise ValueError(
                f"The {self.__class__.__name__} expects a list containing only ChatMessage instances. "
                f"The provided list contains other types. Please ensure that all elements in the list "
                f"are ChatMessage instances."
            )

        processed_messages = []
        if isinstance(template, list):
            for message in template:
                if message.is_from(ChatRole.USER) or message.is_from(ChatRole.SYSTEM):
                    self._validate_variables(set(template_variables_combined.keys()))
                    if message.text is None:
                        raise ValueError(
                            NO_TEXT_ERROR_MESSAGE.format(
                                role=message.role.value, message=message
                            )
                        )
                    if message.text and "templatize_part" in message.text:
                        raise ValueError(FILTER_NOT_ALLOWED_ERROR_MESSAGE)
                    compiled_template = self._env.from_string(message.text)
                    rendered_text = compiled_template.render(
                        template_variables_combined
                    )

                    non_text_contents = [
                        c for c in message._content if not isinstance(c, TextContent)
                    ]
                    rendered_content = [
                        TextContent(text=rendered_text)
                    ] + non_text_contents
                    rendered_message = replace(message, _content=rendered_content)
                    processed_messages.append(rendered_message)
                else:
                    processed_messages.append(message)
        else:
            raise ValueError(
                f"The {self.__class__.__name__} only supports list[ChatMessage] template. "
                f"String templates are not supported for multimodal content."
            )

        return {"prompt": processed_messages}

    def _validate_variables(self, provided_variables: set[str]):
        if self.required_variables == "*":
            required_variables = sorted(self.variables)
        else:
            required_variables = self.required_variables
        missing_variables = [
            var for var in required_variables if var not in provided_variables
        ]
        if missing_variables:
            missing_vars_str = ", ".join(missing_variables)
            raise ValueError(
                f"Missing required input variables in MultimodalChatPromptBuilder: {missing_vars_str}. "
                f"Required variables: {required_variables}. Provided variables: {provided_variables}."
            )

    def to_dict(self) -> dict[str, Any]:
        template: list[dict[str, Any]] | str | None = None
        if isinstance(self.template, list):
            template = [m.to_dict() for m in self.template]
        elif isinstance(self.template, str):
            template = self.template

        return default_to_dict(
            self,
            template=template,
            variables=self._variables,
            required_variables=self._required_variables,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MultimodalChatPromptBuilder":
        init_parameters = data["init_parameters"]
        template = init_parameters.get("template")
        if template:
            if isinstance(template, list):
                init_parameters["template"] = [
                    ChatMessage.from_dict(d) for d in template
                ]
            elif isinstance(template, str):
                init_parameters["template"] = template

        return default_from_dict(cls, data)
