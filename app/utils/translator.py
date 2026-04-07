from deep_translator import GoogleTranslator
import asyncio
import re

async def translate_text(text, src='uk', dest='en'):
    if not text:
        return text
    try:
        loop = asyncio.get_event_loop()
        translated = await loop.run_in_executor(
            None, 
            lambda: GoogleTranslator(source=src, target=dest).translate(text)
        )
        
        translated = re.sub(r'\b(вул\.|вулиця|Street|St\.)\b', 'St', translated, flags=re.IGNORECASE)
        translated = translated.replace("м²", "m²").replace("м2", "m²").replace("sq.m.", "m²")
        
        return translated
    except Exception:
        return text