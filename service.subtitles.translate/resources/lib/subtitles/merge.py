# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023-2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
import io
import itertools

from .subtitle import SrtFrase


MAX_CHARS_PER_LINE = 42

class Sentence:
    """Object to hold one or more SrtFrases forming one complete sentence."""
    def __init__(self, *args):
        self.orig_frases = list(args) if args else []

    @property
    def text(self):
        return ' '.join(line.text for line in self.orig_frases)

    @text.setter
    def text(self, new_text):
        """Spread new_text over all lines in such a way that each line has a relative
        length similar to the original. All in an attempt to keep the timing of the
        new subtitles as close to the original as possible.

        """
        for rel_len, srt_line in zip(self._relative_line_lengths(), self.orig_frases):
            if rel_len == 1:
                # The last segment
                srt_line.text = new_text
                return
            split_pos = int(len(new_text) * rel_len)
            new_text = split_line(srt_line, new_text, split_pos)

    def append_frase(self, frase):
        self.orig_frases.append(frase)

    def _relative_line_lengths(self):
        orig_lines = self.orig_frases
        orig_lengths = [len(line.text) for line in orig_lines]
        relative_lengths = [orig_lengths[i] / sum(orig_lengths[i:]) for i in range(len(orig_lines))]
        # noinspection PyUnboundLocalVariable
        return relative_lengths

    def __bool__(self):
        return bool(self.orig_frases)

    def __str__(self):
        return self.text


class MergedDoc:
    def __init__(self, srt_doc):
        self._srt_doc = srt_doc
        self._sentences = {}
        self._merge_lines()

    def _merge_lines(self):
        idx = 1
        new_sentence = Sentence()
        sentence_map = self._sentences
        for frase in self._srt_doc.frases():
            if not frase:
                # An SrtDoc should not produce emtpy frases, but better be sure.
                continue
            new_sentence.append_frase(frase)
            if frase.text[-1] in ".!?":
                sentence_map[str(idx)] = new_sentence
                new_sentence = Sentence()
                idx += 1

    @property
    def text(self):
        return '\n'.join(itertools.chain.from_iterable((k, v.text) for k, v in self._sentences.items()))

    @text.setter
    def text(self, value):
        with(io.StringIO(value)) as line_iter:
            for line in line_iter:
                line = line.rstrip()
                try:
                    int(line)
                    text = next(line_iter)
                    self._sentences[line].text = text.rstrip()
                except ValueError:
                    continue
                except StopIteration:
                    return


def split_line(srt_frase: SrtFrase,
               new_text: str,
               split_idx: int):
    last_char = srt_frase.text[-1]
    if last_char in ",:;'\"":
        # Try to split on the same character
        new_frase_text, remainder = _split_line_on_character(new_text, last_char, split_idx)
        if new_frase_text:
            srt_frase.text = new_frase_text
            return remainder

    new_frase_text, remainder = _split_on_word(new_text, split_idx)
    srt_frase.text = new_frase_text
    return remainder


def _split_line_on_character(line: str,
                             split_char: str,
                             split_idx: int,
                             max_deviation: int | None = None):
    """Try to split on the occurrence of a character like ',', ':', ';' removing the trailing space.
    The split character is to be within a certain range of the intended split index.

    Return the split part and remainder of the original string. If no split could be made split part is
    an empty string and the remainder is the original string.

    :param line: The line of text to split
    :param split_char: The character that separates the first part and the remainder.
    :param split_idx: The preferred position in `line` to make the split.
    :param max_deviation: The number of character the actual position of `split_char` can
            deviate from the preferred `split_idx`. Defaults to half of `split_idx`.

    """
    if max_deviation is None:
        max_deviation = split_idx / 2
    char_pos = line.rfind(split_char, 0, split_idx)
    if char_pos >= split_idx - max_deviation:
        return line[:char_pos +1], line[char_pos+1:].lstrip()

    char_pos = line.find(split_char, split_idx)
    if 0 < char_pos < split_idx + max_deviation:
        return line[:char_pos +1], line[char_pos+1:].lstrip()
    return '', line


def _split_line_equal(line: str, splits: int):
    parts = []
    while splits > 1:
        part_len = len(line) // splits
        part, line = _split_on_word(line, part_len)
        parts.append(part)
        splits -= 1
    parts.append(line)
    return parts


def _split_on_word(line: str, pos: int):
    """ Search for a word boundary closest to 'pos' and split the line there.

    :param line: the line to be split
    :param pos: the preferred position of the split
    :return: tuple[str, str]

    """
    pos_before = line.rfind(' ', 0, pos + 1)
    if pos_before == -1:
        pos_before = 0

    pos_after = line.find(' ', pos)
    if pos_after == -1:
        pos_after = len(line)

    if pos_before and pos - pos_before < pos_after - pos:
        return line[:pos_before], line[pos_before + 1:]
    else:
        return line[:pos_after], line[pos_after + 1:]