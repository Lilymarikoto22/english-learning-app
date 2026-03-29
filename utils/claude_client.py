import base64
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

DICTATION_MODEL = "claude-sonnet-4-6"
CONVERSATION_MODEL = "claude-haiku-4-5-20251001"
VOCABULARY_MODEL = "claude-haiku-4-5-20251001"

CONVERSATION_SYSTEM_PROMPT = """You are a friendly English conversation partner for a Japanese person learning English.

Rules:
- Always reply in simple, natural English
- Keep sentences short and clear
- After each of your replies, gently point out ONE grammar or vocabulary mistake the user made (if any), in this format:
  💡 **Tip:** [brief correction in Japanese or English]
- If the user made no mistakes, skip the tip
- Be encouraging and warm
- Do not correct more than one mistake per turn
"""

DICTATION_SYSTEM_PROMPT = """You are an English dictation coach helping a Japanese learner.

The user listened to a BBC 6 Minute English podcast and typed what they heard.
Evaluate their dictation response with these guidelines:
- Point out likely spelling errors
- Point out likely missing or wrong words
- Note any grammar issues
- Be encouraging and specific
- Give 2-3 vocabulary tips related to the episode topic
- Keep your response concise and easy to read
- Use Japanese for explanations where helpful

Format your response with clear sections using emoji headers.
"""


def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。")
    return key


def get_dictation_feedback(episode_title: str, user_text: str) -> str:
    """ディクテーションのフィードバックを取得する。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    message = client.messages.create(
        model=DICTATION_MODEL,
        max_tokens=1024,
        system=DICTATION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Episode: {episode_title}\n\nMy dictation:\n{user_text}",
            }
        ],
    )
    return message.content[0].text


def get_example_sentence(word: str, definition: str) -> str:
    """単語の例文を生成する。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    message = client.messages.create(
        model=VOCABULARY_MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Create 2 natural example sentences using the word '{word}' "
                    f"(meaning: {definition}). "
                    "Keep sentences simple and easy for a beginner to understand. "
                    "Add a brief Japanese translation for each sentence."
                ),
            }
        ],
    )
    return message.content[0].text


def transcribe_audio(audio_bytes: bytes) -> str:
    """音声をテキストに文字起こしする。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    audio_b64 = base64.standard_b64encode(audio_bytes).decode("utf-8")
    message = client.messages.create(
        model=DICTATION_MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "source": {
                            "type": "base64",
                            "media_type": "audio/wav",
                            "data": audio_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Transcribe this audio exactly as spoken. Return only the transcription, nothing else.",
                    },
                ],
            }
        ],
    )
    return message.content[0].text


def extract_vocab_from_conversation(messages: list[dict]) -> list[dict]:
    """会話履歴から覚えるべき単語を抽出する。[{"word": ..., "definition": ...}] を返す。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )
    message = client.messages.create(
        model=VOCABULARY_MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    "Look at this English conversation and pick up to 5 useful words or phrases "
                    "that a Japanese beginner should learn. "
                    "For each word, provide a simple Japanese definition and one short example sentence.\n\n"
                    "Reply ONLY with a JSON array like this (no other text):\n"
                    '[{"word": "...", "definition": "日本語の意味 / example sentence"}, ...]\n\n'
                    f"Conversation:\n{conversation_text}"
                ),
            }
        ],
    )
    import json
    text = message.content[0].text.strip()
    # JSON部分だけ抽出
    start = text.find("[")
    end = text.rfind("]") + 1
    return json.loads(text[start:end])


def get_recommended_words(level: str) -> list[dict]:
    """レベル別におすすめ単語を生成する。[{"word": ..., "definition": ...}] を返す。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    level_desc = {
        "初級 (CEFR A1-A2)": "very basic everyday words for absolute beginners",
        "中級 (CEFR B1-B2)": "intermediate words useful for daily conversation and reading news",
        "上級 (CEFR C1-C2)": "advanced vocabulary for fluent expression and academic contexts",
    }
    description = level_desc.get(level, "intermediate words")

    message = client.messages.create(
        model=VOCABULARY_MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate 8 useful English words for a Japanese learner at {level} level ({description}). "
                    "For each word, provide a simple Japanese definition and one short example sentence.\n\n"
                    "Reply ONLY with a JSON array like this (no other text):\n"
                    '[{"word": "...", "definition": "日本語の意味 / example sentence"}, ...]'
                ),
            }
        ],
    )
    import json
    text = message.content[0].text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    return json.loads(text[start:end])


def generate_dialogue(genre: str = "everyday") -> dict:
    """フレーズ学習用のストーリー仕立てダイアログを生成する。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    genre_desc = {
        "everyday":  "casual everyday British life",
        "business":  "professional business or workplace setting",
        "travel":    "travel, holiday, or tourism situation",
        "opinions":  "a discussion where characters share opinions",
        "feelings":  "an emotional or heartfelt moment",
        "social":    "a social situation such as a party, café, or outing",
    }
    context = genre_desc.get(genre, "everyday British life")

    message = client.messages.create(
        model=DICTATION_MODEL,
        max_tokens=1100,
        messages=[
            {
                "role": "user",
                "content": (
                    "Create a British English phrase-learning mini-story dialogue, "
                    "in the style of British Council 'Learn English' podcasts.\n\n"
                    f"Setting: {context}\n\n"
                    "Requirements:\n"
                    "- Build a SHORT STORY with a clear beginning, middle and end — not just a chat\n"
                    "- 7–10 lines between Sophie (F) and James (M)\n"
                    "- Feature ONE key natural British English phrase or expression\n"
                    "- The phrase should arise naturally from the story situation\n"
                    "- Total reading time: about 2 minutes\n"
                    "- Rich, vivid, natural British English — feel free to use humour\n"
                    "- explanation and when_to_use must be written in Japanese\n"
                    "- Include 2 similar expressions\n\n"
                    "Reply ONLY with JSON (no other text):\n"
                    '{"phrase": "...", '
                    '"explanation": "日本語で意味を説明。", '
                    '"when_to_use": "どんな場面で使うか日本語で説明。", '
                    '"similar_expressions": ["expr1", "expr2"], '
                    '"dialogue": ['
                    '{"speaker": "F", "name": "Sophie", "line": "..."}, '
                    '{"speaker": "M", "name": "James", "line": "..."}'
                    "]}"
                ),
            }
        ],
    )
    import json
    text = message.content[0].text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


def translate_dialogue(data: dict) -> str:
    """ダイアログ全体を日本語訳する。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    lines_text = "\n".join(
        f"{d['name']}: {d['line']}" for d in data["dialogue"]
    )
    message = client.messages.create(
        model=VOCABULARY_MODEL,
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Translate the following English dialogue into natural Japanese. "
                    "Keep the speaker names. Return only the translation.\n\n"
                    f"{lines_text}"
                ),
            }
        ],
    )
    return message.content[0].text


def translate_article(article_text: str) -> str:
    """記事を日本語に翻訳する。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    message = client.messages.create(
        model=VOCABULARY_MODEL,
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": (
                    "Translate the following English article into natural Japanese. "
                    "Keep paragraph breaks. Return only the translation, nothing else.\n\n"
                    f"{article_text}"
                ),
            }
        ],
    )
    return message.content[0].text


def extract_business_vocab(article_text: str) -> list[dict]:
    """記事からビジネスでよく使う重要単語を抽出する。[{"word", "definition", "example"}] を返す。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    message = client.messages.create(
        model=VOCABULARY_MODEL,
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": (
                    "From the following English article, extract exactly 10 words or phrases "
                    "that are useful in business or professional contexts.\n\n"
                    "For each word:\n"
                    "- Choose words that appear in business news, meetings, or reports\n"
                    "- Provide a clear Japanese definition\n"
                    "- Provide one short example sentence (different from the article)\n\n"
                    "Reply ONLY with a JSON array (no other text):\n"
                    '[{"word": "...", "definition": "日本語の意味", "example": "Example sentence."}, ...]\n\n'
                    f"Article:\n{article_text}"
                ),
            }
        ],
    )
    import json
    text = message.content[0].text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    return json.loads(text[start:end])


def generate_shadowing_article(topic: str, source_articles: list[dict] | None = None, source_type: str = "bbc") -> dict:
    """シャドウイング練習用の短いニュース記事を生成する。{"title": str, "text": str} を返す。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    if source_articles:
        sources_text = "\n\n".join(
            f"[Source {i+1}] {a['title']} ({a['date']})\n{a['body']}"
            for i, a in enumerate(source_articles)
        )
        if source_type == "ted":
            style = "engaging spoken English in the style of a TED Talk script"
            source_label = "TED Talks"
        else:
            style = "clear, formal BBC broadcast English"
            source_label = "BBC News articles"
        prompt = (
            f"Based ONLY on the following real {source_label}, write a shadowing practice article.\n\n"
            f"{sources_text}\n\n"
            "Requirements:\n"
            "- 170-200 words (about 1 minute 30 seconds when read aloud)\n"
            f"- {style}\n"
            "- Short sentences, easy to shadow\n"
            "- Only include facts from the source articles above — do not invent anything\n"
            "- No bullet points, just flowing paragraphs\n\n"
            "Reply ONLY with JSON in this format (no other text):\n"
            '{"title": "Article title here", "text": "Full article text here"}'
        )
    else:
        prompt = (
            f"Write a short BBC-style news article about '{topic}' for English shadowing practice.\n\n"
            "Requirements:\n"
            "- Exactly 170-200 words (about 1 minute 30 seconds when read aloud)\n"
            "- Clear, formal BBC broadcast English\n"
            "- Short sentences, easy to shadow\n"
            "- No bullet points, just flowing paragraphs\n\n"
            "Reply ONLY with JSON in this format (no other text):\n"
            '{"title": "Article title here", "text": "Full article text here"}'
        )

    message = client.messages.create(
        model=DICTATION_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    import json
    text = message.content[0].text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


def stream_conversation(messages: list[dict]):
    """会話のストリーミングレスポンスを返すジェネレータ。"""
    client = anthropic.Anthropic(api_key=get_api_key())

    with client.messages.stream(
        model=CONVERSATION_MODEL,
        max_tokens=512,
        system=CONVERSATION_SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
