import unicodedata
import re

def strip_diacritics(s: str) -> str:
    # Unicode NFD + odstraň diakritiku
    return ''.join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def normalize_text(text: str) -> str:
    """
    Fixná normalizácia (zodpovedá pôvodnému 'engine.normalization'):
      - lowercase
      - strip diacritics
      - remove punctuation
      - collapse whitespace
    """
    s = text or ""

    # lowercase
    s = s.lower()
    # strip diacritics
    s = strip_diacritics(s)
    # remove punctuation (ponecháme len písmená/čísla/medzery)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    # collapse whitespace
    s = re.sub(r"\s+", " ", s, flags=re.UNICODE).strip()

    return s