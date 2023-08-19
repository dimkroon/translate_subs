# ----------------------------------------------------------------------------------------------------------------------
#  Copyright (c) 2023.
#  This file is part of translate_subs
#  SPDX-License-Identifier: GPL-2.0-or-later
#  See LICENSE.txt
# ----------------------------------------------------------------------------------------------------------------------

import logging
from resources.lib import utils


logger = logging.getLogger('.'.join((utils.logger_id, __name__.split('.', 2)[-1])))


def ttml_to_srt(ttml_data: str) -> str:
    """Convert subtitles in XML format to srt format."""
    from io import StringIO
    from xml.etree import ElementTree
    import re

    # Get XML namespace
    match = re.search(r'xmlns="(.*?)" ', ttml_data, re.DOTALL)
    if match:
        xmlns = ''.join(('{', match.group(1), '}'))
    else:
        xmlns = ''

    FONT_COL_WHITE = '<font color="white">'
    FONT_END_TAG = '</font>\n'

    root = ElementTree.fromstring(ttml_data)

    dflt_styles = {}
    path = ''.join(('./', xmlns, 'head', '/', xmlns, 'styling', '/', xmlns, 'style'))
    styles = root.findall(path)
    for style_def in styles:
        style_id = style_def.get(xmlns + 'id')
        colors = [value for tag, value in style_def.items() if tag.endswith('color')]
        if colors:
            col = colors[0]
            # strip possible alpha value if color is a HTML encoded RBGA value
            if col.startswith('#'):
                col = col[:7]
            dflt_styles[style_id] = ''.join(('<font color="', col, '">'))

    body = root.find(xmlns + 'body')
    if body is None:
        return ''

    index = 0
    # lines = []
    color_tag = "{http://www.w3.org/ns/ttml#styling}" + 'color'

    with StringIO() as outfile:
        for paragraph in body.iter(xmlns + 'p'):
            index += 1

            t_start = paragraph.get('begin')
            t_end = paragraph.get('end')
            if not (t_start and t_end):
                continue
            outfile.write(str(index) + '\n')
            # convert xml time format: begin="00:03:33:14" end="00:03:36:06"
            # to srt format: 00:03:33,140 --> 00:03:36,060
            outfile.write(''.join((t_start[0:-3], ',', t_start[-2:], '0', ' --> ', t_end[0:-3], ',', t_end[-2:], '0\n')))

            p_style = paragraph.get('style')
            p_col = dflt_styles.get(p_style, FONT_COL_WHITE)
            if paragraph.text:
                outfile.write(''.join((p_col, paragraph.text, FONT_END_TAG)))
            for el in paragraph:
                if el.tag.endswith('span') and el.text:
                    col = el.get(color_tag, 'white')
                    # col = [v for k, v in el.items() if k.endswith('color')]
                    # if col:
                    outfile.write(''.join(('<font color="', col, '">', el.text, FONT_END_TAG)))
                    # else:
                    #     lines.append(''.join((FONT_COL_WHITE, el.text, FONT_END_TAG)))
                if el.tail:
                    outfile.write(''.join((p_col, el.tail, FONT_END_TAG)))
            outfile.write('\n')
        return outfile.getvalue()


def vtt_to_srt(vtt_doc: str, colourize=True) -> str:
    """Convert a string containing subtitles in vtt format into a format kodi accepts.

    Very simple converter that does not expect much styling, position, etc. and tries
    to ignore most fancy vtt stuff. But seems to be enough for most itv subtitles.

    All styling, except bold, italic, underline and colour in the cue payload is
    removed, as well as position information.

    """
    from io import StringIO
    import re

    # Match a line that start with cue timings. Accept timings with or without hours.
    regex = re.compile(r'(\d{2})?:?(\d{2}:\d{2})\.(\d{3}) +--> +(\d{2})?:?(\d{2}:\d{2})\.(\d{3})')

    # Convert new lines conform WebVTT specs
    vtt_doc = vtt_doc.replace('\r\n', '\n')
    vtt_doc = vtt_doc.replace('\r', '\n')

    # Split the document into blocks that are separated by an empty line.
    vtt_blocks = vtt_doc.split('\n\n')
    seq_nr = 0

    with StringIO() as f:
        for block in vtt_blocks:
            lines = iter(block.split('\n'))

            # Find cue timings, ignore all cue settings.
            try:
                line = next(lines)
                timings_match = regex.match(line)
                if not timings_match:
                    # The first line may be a cue identifier
                    line = next(lines)
                    timings_match = regex.match(line)
                    if not timings_match:
                        # Also no timings in the second line: this is not a cue block
                        continue
            except StopIteration:
                # Not enough lines to find timings: this is not a cue block
                continue

            # Write newline and sequence number
            seq_nr += 1
            f.write('\n{}\n'.format(seq_nr))
            # Write cue timings, add "00" for missing hours.
            f.write('{}:{},{} --> {}:{},{}\n'.format(*timings_match.groups('00')))
            # Write out the lines of the cue payload
            for line in lines:
                f.write(line + '\n')

        srt_doc = f.getvalue()

    if colourize:
        # Remove any markup tag other than the supported bold, italic underline and colour.
        srt_doc = re.sub(r'<([^biuc]).*?>(.*?)</\1.*?>', r'\2', srt_doc)

        # convert color tags, accept only simple colour names.
        def sub_color_tags(match):
            colour = match[1]
            if colour in ('white', 'yellow', 'green', 'cyan', 'red'):
                # Named colours
                return '<font color="{}">{}</font>'.format(colour, match[2])
            elif colour.startswith('color'):
                # RBG colour, ensure to strip the alpha channel if present.
                result = '<font color="#{}">{}</font>'.format(colour[5:11], match[2])
                return result
            else:
                logger.debug("Unsupported colour '%s' in vtt file", colour)
                return match[2]

        srt_doc = re.sub(r'<c\.(.*?)>(.*?)</c>', sub_color_tags, srt_doc)
    else:
        # Remove any markup tag other than the supported bold, italic underline.
        srt_doc = re.sub(r'<([^biu]).*?>(.*?)</\1.*?>', r'\2', srt_doc)
    return srt_doc


def convert_subs(doc: str, doc_type: str):
    doc_type = doc_type.lstrip('.')
    if doc_type == 'ttml':
        return ttml_to_srt(doc)
    if doc_type == 'vtt':
        return vtt_to_srt(doc)
    else:
        raise ValueError("Unsupported subtitles type '{}'".format(doc_type))