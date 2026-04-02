from chat2rag.core.logger import get_logger
from chat2rag.providers.tts import BaseTTS, CosyVoiceTTS
from chat2rag.schemas.chat import Audio

logger = get_logger(__name__)


class TTSFactory:
    PROVIDERS = {
        "cosy_voice_tts": CosyVoiceTTS,
    }

    @staticmethod
    def create(audio_config: Audio) -> BaseTTS | None:
        provider_name = audio_config.provider

        provider_class = TTSFactory.PROVIDERS.get(provider_name)

        if not provider_class:
            logger.warning(
                f"Unknown TTS provider: {provider_name}, "
                f"available providers: {list(TTSFactory.PROVIDERS.keys())}"
            )
            return None

        try:
            tts_instance = provider_class(audio_config)
            logger.info(
                f"TTS provider created: {provider_name}, "
                f"voice={audio_config.voice}, format={audio_config.format}"
            )
            return tts_instance
        except Exception:
            logger.exception(f"Failed to create TTS provider: {provider_name}")
            return None

    @staticmethod
    def register_provider(name: str, provider_class: type):
        if name in TTSFactory.PROVIDERS:
            logger.warning(f"TTS provider {name} already registered, overwriting")

        TTSFactory.PROVIDERS[name] = provider_class
        logger.info(f"TTS provider registered: {name}")

    @staticmethod
    def get_available_providers() -> list[str]:
        return list(TTSFactory.PROVIDERS.keys())
