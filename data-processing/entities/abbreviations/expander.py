import logging
from typing import Iterator, List

import pysbd

from common.parse_tex import DEFAULT_CONTEXT_SIZE, EntityExtractor, PlaintextExtractor

from .types import Abbreviation

import spacy
from scispacy.abbreviation import AbbreviationDetector
import re
import sys
from TexSoup import *

class AbbreviationExpander(EntityExtractor):

    def parse(self, tex_path: str, tex: str, abb) -> Iterator[Abbreviation]:
        for reserved_char in PYSBD_RESERVED_CHARACTERS:
            if reserved_char in tex:
                logging.warning(
                    'Reserved character from pysbd "%s" found in tex string, this might break the sentence extractor.',
                    reserved_char,
                )
