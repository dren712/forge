import httpx
import os
from typing import Optional
from app.core.logging import get_logger

logger = get_logger("forge.voice")


class SmallestAIVoiceService:
    """
    Synthesizes natural voice debriefs for agent evolution milestones using Smallest.ai (Waves API).
    Provides real-time audio commentary on why an agent failed or how a mutation improved accuracy.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SMALLEST_API_KEY", "")
        self.base_url = "https://api.smallest.ai/waves/v1/lightning-v3.1/get_speech"

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("sk_placeholder"))

    async def generate_narration(self, text: str, voice_id: str = "sophia") -> bytes | None:
        if not self.is_configured():
            logger.warning("SMALLEST_API_KEY is not configured.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "voice_id": voice_id,
            "sample_rate": 24000,
            "output_format": "wav",
            "add_wav_header": True,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Smallest.ai error {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to generate voice narration: {e}")
            return None


voice_service = SmallestAIVoiceService()
