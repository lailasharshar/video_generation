from dotenv import load_dotenv
import requests
import os

load_dotenv()

# This is a standard voice, but not too familiar
DEFAULT_AUDIO = 'ThT5KcBeYPX3keUQqHPh' # Dorothy


class ElevenLabsAPI:
    # Set up the API Key and the header info
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")

        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    # Retrieve all the voices you have access to. You can add ones from the community if you'd like but
    # by default, it will have the basic ones
    def get_voices(self):
        """Get available voices"""
        response = requests.get(
            f"{self.base_url}/voices",
            headers=self.headers
        )
        return response.json()

    # Given the text and the voice to use, return the content of the audio
    def generate_speech(self, text, voice_id=DEFAULT_AUDIO,
                        model_id="eleven_monolingual_v1"):
        url = f"{self.base_url}/text-to-speech/{voice_id}"

        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        response = requests.post(url, json=data, headers=self.headers)

        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Error generating speech: {response.text}")