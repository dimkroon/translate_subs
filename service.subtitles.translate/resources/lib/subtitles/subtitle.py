# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import re

class SrtLine:
    def __init__(self, lead, text, tail, ignore_colours=False):
        idx = None
        self._ignore_col = ignore_colours
        if lead and tail:
            self.lead = lead
            self._text = text
            self.tail = tail
        else:
            self.lead = ''
            self._text = ''.join((lead, text, tail))
            self.tail = ''
        self.merged = False

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
                return ''.join((self.lead, self._text, self.tail))
        else:
            return ''

    def __bool__(self):
        return bool(self._text)


class SrtBlock:
    def __init__(self, block_str, ignore_colours=False):
        self.idx = ''
        self._time = ''
        self.lines = []
        self._parse(block_str, ignore_colours)

    def _parse(self, block_str: str, ignore_col):
        lines = block_str.strip().split('\n', maxsplit=2)
        self.idx = lines[0]
        self._time = lines[1]
        try:
            matches = re.findall(r'(^<[^/<>]+>)?(.+?)(</[^<>]+>)?$', lines[2], re.MULTILINE)
            self.lines = [SrtLine(*match, ignore_colours=ignore_col) for match in matches]
        except IndexError:
            # A block with index, (possibly empty) time, but no text. Does happen...
            self.lines = []

    def __str__(self):
        if self.idx and self._time:
            return '\n'.join((self.idx, self._time, *(str(line) for line in self.lines if line), '\n'))
        else:
            return ''

    @property
    def text(self):
        # return '\n'.join((self._idx, *(line.text for line in self.lines),'\n'))
        lines = self.lines
        if not lines:
            return '\n'.join((self.idx, '\n'))
        texts = [lines[0].text]
        for i in range(1, len(lines)):
            prev_line = lines[i-1]
            cur_line = lines[i]
            # Merge lines of the same actor (same text colour) when the previous line was not the end of a sentence.
            if cur_line.lead == prev_line.lead and prev_line.text[-1] not in ('.', '!', '?'):
                cur_line.merged = True
                texts[-1] = ' '.join((texts[-1], cur_line.text))
            else:
                texts.append(cur_line.text)
        return '\n'.join((self.idx, *texts, '\n'))

    @text.setter
    def text(self, trans_block):
        orig_lines = self.lines
        num_orig_lines = len(orig_lines)
        trans_lines = trans_block.lines

        if num_orig_lines == len(trans_lines):
            for i in range(num_orig_lines):
                orig_lines[i].text = trans_lines[i]
        else:
            j = 0
            for line in trans_lines:
                # find the all corresponding original lines
                lines_list = [orig_lines[j]]
                j += 1
                while j < num_orig_lines and orig_lines[j].merged:
                    lines_list.append(orig_lines[j])
                    j += 1
                # split the translated line into the same number of parts
                num_merged_lines = len(lines_list)
                new_texts = split_line(line, num_merged_lines)
                # and apply the translated text to the original line.
                for i in range(num_merged_lines):
                    lines_list[i].text = new_texts[i]


class SrtDoc:
    def __init__(self, srt_doc: str, ignore_colours=False):
        blocks = srt_doc.split('\n\n')
        self.blocks = [SrtBlock(block, ignore_colours) for block in blocks if block]

    @property
    def text(self):
        return ''.join(block.text for block in self.blocks)

    @text.setter
    def text(self, value):
        for orig, trans in zip(self.blocks, value.blocks):
            orig.text = trans

    def sentences(self):
        text_parts = []
        for block in self.blocks:
            for line in block.lines:
                line_idx = 0
                text = line.text
                text_parts.append(f"<a b={block.idx} l={line_idx}>{text} </a>")
                if text[-1] in (".!?"):
                    text = ''.join(text_parts)
                    yield text
                    text_parts.clear()
        if text_parts:
            yield ''.join(text_parts)

    def __str__(self):
        return ''.join(str(block) for block in self.blocks)


class TransBlock:
    def __init__(self, block_str, block_idx='',  html=False):
        self.idx = block_idx
        self.lines = []
        if not html:
            self._parse(block_str)
        else:
            self.lines = [block_str]

    def _parse(self, block_str: str):
        block_str = block_str.strip()
        lines = block_str.split('\n')
        if lines:
            self._idx = lines[0]
            self.lines = lines[1:]


class TransDoc:

    def __init__(self, doc_str: str, html=False):
        if not html:
            self.blocks = [TransBlock(block) for block in doc_str.split('\n\n')]
        else:
            self.blocks = []
            self._parse_html(doc_str)

    def _parse_html(self, doc_str):
        regex = re.compile(r'<a b\s?=\s?(\d+) ?l\s?=\s?(\d)>(.*)')
        lines = iter(doc_str.split('</a>'))
        try:
            l = next(lines)
            block_idx, line_idx, text = re.search(regex, l).groups()
            while l:
                cur_block = TransBlock(text, block_idx, True)
                self.blocks.append(cur_block)
                for l in lines:
                    if not l:
                        return
                    match = re.search(regex, l)
                    block_idx, line_idx, text = match.groups()
                    if cur_block.idx == block_idx:
                        cur_block.lines.append(text)
                    else:
                        break
        except StopIteration:
            pass






def split_line(line: str, splits: int):
    result = _split_line_on_comma(line, splits)
    if not result:
        result = _split_line_equal(line, splits)
    return result


def _split_line_on_comma(line: str, splits: int):
    # Try to split on the occurrence of ', ' keeping the comma and removing the space.
    parts = re.split(r'(?<=,) ', line)

    if len(parts) == 1:
        return False

    while len(parts) > splits:
        # merge the smallest parts
        min_len = MAX_CHARS_PER_LINE
        merge_idx = 0
        for i in range(len(parts) - 1):
            new_len = len(parts[i]) + len(parts[i+1])
            if new_len < min_len:
                min_len = new_len
                merge_idx = i
        parts[merge_idx] = ' '.join(parts[merge_idx:merge_idx + 2])
        parts.pop(merge_idx + 1)

    for part in parts:
        if len(part) > MAX_CHARS_PER_LINE:
            return False

    if len(parts) < splits:
        parts += [''] * (splits - len(parts))
    return parts


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


def split_srt_doc(src_txt: str, max_len):
    """Split string `src_txt` into pieces of text with no more than `max_len` characters. Split only
    on a double newline sequence closest to `max_len`, thus ensuring the split parts contain complete
    blocks of an srt or vtt file.

    Returns a list of strings.

    """
    txt_len = len(src_txt)
    if txt_len <= max_len:
        return [src_txt]

    splits = []
    start_pos = 0

    while txt_len - start_pos > max_len:
        split_pos = src_txt.rfind('\n', start_pos, start_pos + max_len)
        if split_pos <= start_pos:
            raise ValueError("No position to split available in src_str")
        splits.append(src_txt[start_pos:split_pos])
        start_pos = split_pos
    splits.append(src_txt[start_pos:])
    return splits

