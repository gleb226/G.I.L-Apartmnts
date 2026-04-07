import json

import os

LOCALES_PATH = os.path.join(os.path.dirname(__file__), 'locales.json')


def load_locales():
    with open(LOCALES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


TEXTS = load_locales()


def get_text(key, lang='uk', **kwargs):
    

    lang_texts = TEXTS.get(lang, TEXTS.get('uk', {}))

    text = lang_texts.get(key, TEXTS.get('uk', {}).get(key, key))

    if kwargs:

        try:

            return text.format(**kwargs)

        except KeyError:

            return text

    return text


def get_all_translations(key):

    translations = []

    for lang in TEXTS:

        if key in TEXTS[lang]:
            translations.append(TEXTS[lang][key])

    return list(set(translations))