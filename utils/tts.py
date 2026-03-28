import asyncio
import edge_tts

VOICE = "en-GB-SoniaNeural"
FEMALE_VOICE = "en-GB-SoniaNeural"
MALE_VOICE = "en-GB-RyanNeural"

SPEED_TO_RATE = {
    0.75: "-25%",
    1.0:  "+0%",
    1.25: "+25%",
    1.5:  "+50%",
}


async def _synthesize_bytes(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return audio


def _run(coro):
    """新しいイベントループでコルーチンを実行する。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def generate_audio(text: str, speed: float = 1.0) -> bytes:
    """テキストから MP3 バイトを生成して返す。"""
    rate = SPEED_TO_RATE.get(speed, "+0%")
    return _run(_synthesize_bytes(text, VOICE, rate))


def generate_dialogue_audio(lines: list[dict], speed: float = 1.0) -> bytes:
    """ダイアログの各セリフを男女の声で並列生成して1つの MP3 バイトにまとめる。

    lines: [{"speaker": "F" or "M", "line": str}, ...]
    """
    rate = SPEED_TO_RATE.get(speed, "+0%")

    async def _build() -> bytes:
        tasks = [
            _synthesize_bytes(
                item["line"],
                FEMALE_VOICE if item["speaker"] == "F" else MALE_VOICE,
                rate,
            )
            for item in lines
        ]
        results = await asyncio.gather(*tasks)
        return b"".join(results)

    return _run(_build())
