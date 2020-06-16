import logging
from typing import Iterator, List

import pysbd

from common.parse_tex import DEFAULT_CONTEXT_SIZE, EntityExtractor, PlaintextExtractor

from .types import Expansion

import spacy
from scispacy.abbreviation import AbbreviationDetector
import re
import sys
from TexSoup import *

PYSBD_RESERVED_CHARACTERS: List[str] = [
    "∯",
    "ȸ",
    "♨",
    "☝",
    "✂",
    "⎋",
    "ᓰ",
    "ᓱ",
    "ᓳ",
    "ᓴ",
    "ᓷ",
    "ᓸ",
]

symbols = ["%", "^", "{", "}", "[", "]", "\\", "=", "#", "&", "~", "$", "|", "_", ":", ";"]

class AbbreviationExpander(EntityExtractor):

    def parse(self, tex_path: str, tex: str) -> Iterator[Expansion]:
        for reserved_char in PYSBD_RESERVED_CHARACTERS:
            if reserved_char in tex:
                logging.warning(
                    'Reserved character from pysbd "%s" found in tex string, this might break the sentence extractor.',
                    reserved_char,
                )
        # Extract plaintext segments from TeX
        #plaintext_extractor = PlaintextExtractor()

        #this is the most basic model and had no real performance difference on our inputs
        #other options include NER models and models with pretrained word vectors
        nlp = spacy.load("en_core_sci_sm")
        abbreviation_pipe = AbbreviationDetector(nlp)
        nlp.add_pipe(abbreviation_pipe)

        cons = tex
        soup = TexSoup(cons)
        soup_text = []
        self.get_text(soup, soup_text)
        contents = ""
        for p, l in soup_text:
            contents += p

        contents = re.sub("\n", " ", contents)
        abb_short_forms = {}
        abb_expansions = {}
        expanded_loc = {}
        doc = nlp(contents)
        for abrv in doc._.abbreviations:
            count = 0
            for s in symbols:
                count += str(abrv).count(s)
            if count == 0:
                abb_short_forms[str(abrv)] = [[m.start(), m.start() + len(str(abrv))] for m in re.finditer(str(abrv), cons)]
                abb_expansions[str(abrv)] = abrv._.long_form
                x = cons.find(str(abrv._.long_form))
                if x != -1:
                    expanded_loc[str(abrv)] = [x, x + len(str(abrv._.long_form))]
                else:
                    for p, l in soup_text:
                        x = p.find(str(abrv._.long_form))
                        if x!= -1:
                            expanded_loc[str(abrv)] = [l + x, l + x + len(str(abrv._.long_form))]
                        else:
                            expanded_loc[str(abrv)] = [0, 0]

        count = 0
        for abb in abb_short_forms:
            start, end = expanded_loc[abb]
            tex_sub = cons[start:end]
            context_tex = cons[start - DEFAULT_CONTEXT_SIZE : end + DEFAULT_CONTEXT_SIZE]
            yield Expansion(
                text = abb_expansions[abb],
                abb = abb,
                abb_locations = abb_short_forms[abb],
                start=start,
                end=end,
                id_= count,
                tex_path=tex_path,
                tex=tex_sub,
                context_tex=context_tex,
            )
            count += 1

    def get_text(self, soup, soup_text):
        for descendant in soup.contents:
            if isinstance(descendant, TokenWithPosition):
                soup_text.append([descendant, descendant.position])
            elif hasattr(descendant, 'text'):
                self.get_text(descendant, soup_text)
