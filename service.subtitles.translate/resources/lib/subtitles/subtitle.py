# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023-2024 Dimitri Kroon.
#  This file is part of service.subtitles.translate.
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations

import logging
import re

from resources.lib import utils


logger = logging.getLogger('.'.join((utils.logger_id, __name__.split('.', 2)[-1])))

# Regex to parse a line with optional multiple tags of various types, like colour, bold, etc.
# Only font (colour) tags are captured, all other tags are disregarded. I'm not quite sure if and how
# to handle other markup tags, as it's very hard to apply them correctly to translated text if the
# tag did not apply to the whole sentence.

# Consists of 4 groups
# A match produces either group 1-3 empty and group 4 having content,
# or groups 1-3 with content and an empty group 4.
# If group 4 has content the regex matched text not enclosed in tags
# If groups 1-3 have content, group 1 contains the opening tag, group2 the actual text and group 3 the closing tag.
# The regex is lenient with regard to extra white space within tags.
line_regex = re.compile(r'(<\s*font[^>]*>)(?:<\s*[^/f][^>]*>)?(.*?)(?:<\s*/[^f][^>]*>)?((?(1)<\s*/font\s*)+>)|(?:^|(?<=>))([^<>]+)')


# line_regex = re.compile(r'((?:<\s*[^/][^>]*>)+)(.*?)((?:<\s*/[\w]+>)+)|([^<]+)')
#?:<\s*[^/f][^>]*>)?(<\s*font[^>]*>)(?:<\s*[^/f][^>]*>)?(.*?)(?:<\s*/[^f][^>]*>)?((?(1)<\s*/font\s*)+>)(?:<\s*/[^f][^>]*>)?|(?:^|(?<=>))([^<>]+)


class SrtFrase:
    def __init__(self, text: str,
                 open_tags: str | None,
                 closing_tags: str | None,
                 ignore_colours: bool = False):
        self._ignore_col = ignore_colours
        self.open_tags = open_tags or ''
        self._text = text.strip()
        self.closing_tags = closing_tags or ''

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    def __str__(self):
        if self._text:
            if self._ignore_col:
                return self._text
            else:
                return ''.join((self.open_tags, self._text, self.closing_tags))
        else:
            return ''

    def __bool__(self):
        return bool(self._text)


class SrtLine:
    def __init__(self, text, ignore_colours=False):
        self._ignore_col = ignore_colours
        self._frases = []
        self._parse_text(text, ignore_colours)

    def _parse_text(self, text, ignor_col):
        for match in line_regex.finditer(text):
            text = match.group(4) or match.group(2)
            text = text.strip()
            if text:
                self._frases.append((SrtFrase(text, match.group(1), match.group(3), ignor_col)))

    def __str__(self):
        if self._frases:
            return ' '.join(str(frase) for frase in self._frases)
        else:
            return ''

    def __bool__(self):
        return bool(self._frases)

    def __iter__(self):
        return iter(self._frases)


class SrtBlock:
    def __init__(self, block_str, ignore_colours=False):
        self.idx = ''
        self.start_time = None
        self.end_time = None
        self.lines = []
        self._parse(block_str, ignore_colours)

    def _parse(self, block_str: str, no_col):
        lines = block_str.strip().split('\n')
        try:
            self.idx = lines[0]
            self._parse_time_line(lines[1])
            for line in lines[2:]:
                line_obj = SrtLine(line.strip(), ignore_colours=no_col)
                if line_obj:
                    self.lines.append(line_obj)
        except IndexError:
            # A block with index, (possibly empty) time, but no text. Does happen...
            pass

    def _parse_time_line(self, time_line):
        start_str, end_str = time_line.split("-->")
        self.start_time = self._parse_time(start_str)
        self.end_time = self._parse_time(end_str)

    def _parse_time(self, time_str: str) -> float:
        """Take a string formatted as %H:%M:%s.%f and return the number of seconds"""
        hours, minutes, second = time_str.replace(',', '.').split(':')
        return int(hours) * 3600 + int(minutes) * 60 + float(second)

    def _format_time_line(self):
        st = self.start_time
        et = self.end_time
        line = f'{st//3600:02.0f}:{st%3600//60:02.0f}:{st%60:06.3f} --> {et//3600:02.0f}:{et%3600//60:02.0f}:{et%60:06.3f}'
        return line.replace('.', ',')

    def __str__(self):
        if self:
            return '\n'.join((self.idx, self._format_time_line(), *(str(line) for line in self.lines if line), '\n'))
        else:
            return ''

    def __iter__(self):
        for line in self.lines:
            yield from line

    def __bool__(self):
        return bool(self.lines)

class SrtDoc:
    def __init__(self, srt_doc: str, ignore_colours=False):
        blocks = srt_doc.split('\n\n')
        self.blocks = list(filter(bool, (SrtBlock(block, ignore_colours) for block in blocks if block)))

    @property
    def text(self):
        return ''.join(block.text for block in self.blocks)

    @text.setter
    def text(self, value):
        for orig, trans in zip(self.blocks, value.blocks):
            orig.text = trans

    def __str__(self):
        def block_iter():
            # re-index and return all non-empty blocks as string
            idx = 1
            for block in self.blocks:
                if block:
                    block.idx = str(idx)
                    idx += 1
                    yield str(block)

        return ''.join(block_str for block_str in block_iter())

    def frases(self):
        """Generator that iterates over all frases in the document."""
        for block in self.blocks:
            for line in block.lines:
                yield from line

    def stretch_time(self, display_time: float):
        """Increase the time subtitles are shown to `display_time` number
        of seconds whenever possible.

        If the gap between one block of subtitles and the next is less than
        `display_time`, stretch the time the first block is shown to fill the gap.

        """
        blocks_iter = iter(self.blocks)
        b1 = next(blocks_iter)
        for b2 in blocks_iter:
            if not b2:
                continue
            et = b1.end_time
            st = b2.start_time
            if st > et:
                new_end_t = min(b1.start_time + display_time, st)
                b1.end_time = new_end_t
                logger.debug("stretched display endTime from %02.0f:%02.0f:%06.3f to %02.0f:%02.0f:%06.3f",
                             et/3600, (et%3600)/60, et%60, new_end_t/3600, (new_end_t%3600)/60, new_end_t%60)
            b1 = b2