import asyncio
import tempfile
import os
import edge_tts

# BBC アナウンサー風の英国英語音声
VOICE = "en-GB-SoniaNeural"
FEMALE_VOICE = "en-GB-SoniaNeural"
MALE_VOICE = "en-GB-RyanNeural"

SPEED_TO_RATE = {
    0.75: "-25%",
    1.0:  "+0%",
    1.25: "+25%",
    1.5:  "+50%",
}


async def _synthesize(text: str, rate: str, output_path: str) -> None:
    communicate = edge_tts.Communicate(text, VOICE, rate=rate)
    await communicate.save(output_path)


def generate_audio(text: str, speed: float = 1.0) -> str:
    """テキストから MP3 ファイルを生成してパスを返す。"""
    rate = SPEED_TO_RATE.get(speed, "+0%")

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()

    # Streamlit の既存イベントループと競合しないよう新しいループで実行
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_synthesize(text, rate, tmp.name))
    finally:
        loop.close()

    return tmp.name


async def _line_to_bytes(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return audio


def generate_dialogue_audio(lines: list[dict], speed: float = 1.0) -> str:
    """ダイアログの各セリフを男女の声で生成して1つの MP3 ファイルにまとめる。

    lines: [{"speaker": "F" or "M", "line": str}, ...]
    """
    rate = SPEED_TO_RATE.get(speed, "+0%")

    async def _build() -> bytes:
        tasks = [
            _line_to_bytes(
                item["line"],
                FEMALE_VOICE if item["speaker"] == "F" else MALE_VOICE,
                rate,
            )
            for item in lines
        ]
        results = await asyncio.gather(*tasks)
        return b"".join(results)

    loop = asyncio.new_event_loop()
    try:
        audio_bytes = loop.run_until_complete(_build())
    finally:
        loop.close()

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.write(audio_bytes)
    tmp.close()
    return tmp.name
