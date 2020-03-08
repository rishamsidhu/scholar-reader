import logging
from dataclasses import dataclass
from typing import Iterator

import pysbd

from common.parse_tex import DEFAULT_CONTEXT_SIZE, EntityExtractor, PlaintextExtractor
from common.types import SerializableEntity


@dataclass(frozen=True)
class Sentence(SerializableEntity):
    text: str


class SentenceExtractor(EntityExtractor):
    """
    Extract plaintext sentences from TeX, with offsets of the characters they correspond to in
    the input TeX strings. The extracted sentences might include some junk TeX, having the same
    limitations as the plaintext produced by PlaintextExtractor.
    """

    def parse(self, tex_path: str, tex: str) -> Iterator[Sentence]:
        # Extract plaintext segments from TeX
        plaintext_extractor = PlaintextExtractor()
        plaintext_segments = plaintext_extractor.parse(tex_path, tex)

        # Build a map from character offsets in the plaintext to TeX offsets. This will let us
        # map from the character offsets of the sentences returned from the sentence boundary
        # detector back to positions in the original TeX.
        plaintext_to_tex_offset_map = {}
        plaintext = ""
        last_segment = None
        for segment in plaintext_segments:
            for i in range(len(segment.text)):
                tex_offset = (
                    (segment.tex_start + i)
                    if not segment.transformed
                    else segment.tex_start
                )
                plaintext_to_tex_offset_map[len(plaintext) + i] = tex_offset

            # While building the map, also create a contiguous plaintext string
            plaintext += segment.text
            last_segment = segment

        if last_segment is not None:
            plaintext_to_tex_offset_map[len(plaintext)] = last_segment.tex_end

        # Segment the plaintext. Return offsets for each setence relative to the TeX input
        segmenter = pysbd.Segmenter(language="en", clean=False, char_span=True)
        for i, sentence in enumerate(segmenter.segment(plaintext)):

            # There's a known issue in pySBD (https://github.com/nipunsadvilkar/pySBD/issues/49)
            # where in some special cases, the character offset counter resets. Detect if it
            # resets and for now, stop sentence extraction. Keep an eye on releases of pySBD,
            # as we definitely want to use a fixed version so we don't skip sentences.
            if i > 0 and sentence.start == 0:
                logging.warning(  # pylint: disable=logging-not-lazy
                    "Known issue from pySBD encountered "
                    + "(https://github.com/nipunsadvilkar/pySBD/issues/49). All upcoming sentences "
                    + "starting at the %dth will not be extracted.",
                    i,
                )
                return

            start = plaintext_to_tex_offset_map[sentence.start]
            end = plaintext_to_tex_offset_map[sentence.end]
            sentence_tex = tex[start:end]
            context_tex = tex[start - DEFAULT_CONTEXT_SIZE : end + DEFAULT_CONTEXT_SIZE]

            yield Sentence(
                text=sentence.sent,
                start=start,
                end=end,
                id_=str(i),
                tex_path=tex_path,
                tex=sentence_tex,
                context_tex=context_tex,
            )
