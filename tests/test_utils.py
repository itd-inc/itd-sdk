from itd.utils import parse_html, parse_md
from itd.enums import SpanType


# --- parse_html ---

def test_parse_html_plain_text():
    text, spans = parse_html('Hello world')
    assert text == 'Hello world'
    assert spans == []


def test_parse_html_empty():
    text, spans = parse_html('')
    assert text == ''
    assert spans == []


def test_parse_html_bold():
    text, spans = parse_html('<b>bold</b>')
    assert text == 'bold'
    assert len(spans) == 1
    assert spans[0].type == SpanType.BOLD
    assert spans[0].offset == 0
    assert spans[0].length == 4


def test_parse_html_italic():
    text, spans = parse_html('<i>italic</i>')
    assert text == 'italic'
    assert spans[0].type == SpanType.ITALIC


def test_parse_html_strike():
    text, spans = parse_html('<s>strike</s>')
    assert text == 'strike'
    assert spans[0].type == SpanType.STRIKE


def test_parse_html_underline():
    text, spans = parse_html('<u>under</u>')
    assert text == 'under'
    assert spans[0].type == SpanType.UNDERLINE


def test_parse_html_monospace():
    text, spans = parse_html('<code>code</code>')
    assert text == 'code'
    assert spans[0].type == SpanType.MONOSPACE


def test_parse_html_link():
    text, spans = parse_html('<a href="https://example.com">click</a>')
    assert text == 'click'
    assert spans[0].type == SpanType.LINK
    assert spans[0].url == 'https://example.com'


def test_parse_html_span_offset():
    text, spans = parse_html('hello <b>world</b>')
    assert text == 'hello world'
    assert spans[0].offset == 6
    assert spans[0].length == 5


def test_parse_html_nested():
    text, spans = parse_html('<b>bold <i>both</i></b>')
    assert text == 'bold both'
    assert len(spans) == 2


# --- parse_md ---

def test_parse_md_plain():
    text, spans = parse_md('Hello world')
    assert text == 'Hello world'
    assert spans == []


def test_parse_md_empty():
    text, spans = parse_md('')
    assert text == ''
    assert spans == []


def test_parse_md_bold():
    text, spans = parse_md('**bold**')
    assert text == 'bold'
    assert len(spans) == 1
    assert spans[0].type == SpanType.BOLD
    assert spans[0].offset == 0
    assert spans[0].length == 4


def test_parse_md_italic():
    text, spans = parse_md('*italic*')
    assert text == 'italic'
    assert spans[0].type == SpanType.ITALIC


def test_parse_md_strike():
    text, spans = parse_md('~~strike~~')
    assert text == 'strike'
    assert spans[0].type == SpanType.STRIKE


def test_parse_md_underline():
    text, spans = parse_md('__under__')
    assert text == 'under'
    assert spans[0].type == SpanType.UNDERLINE


def test_parse_md_monospace():
    text, spans = parse_md('`code`')
    assert text == 'code'
    assert spans[0].type == SpanType.MONOSPACE


def test_parse_md_spoiler():
    text, spans = parse_md('||spoiler||')
    assert text == 'spoiler'
    assert spans[0].type == SpanType.SPOILER


def test_parse_md_link():
    text, spans = parse_md('[click](https://example.com)')
    assert text == 'click'
    assert spans[0].type == SpanType.LINK
    assert spans[0].url == 'https://example.com'


def test_parse_md_link_empty_url():
    text, spans = parse_md('[text]()')
    assert text == 'text'
    assert spans[0].url == 'text'


def test_parse_md_span_offset():
    text, spans = parse_md('hello **world**')
    assert text == 'hello world'
    assert spans[0].offset == 6
    assert spans[0].length == 5


def test_parse_md_escape():
    text, spans = parse_md(r'\**not bold**')
    assert text.startswith('*')
    assert not any(s.type == SpanType.BOLD for s in spans)


def test_parse_md_nested():
    text, spans = parse_md('**bold *both* end**')
    assert 'bold' in text
    assert any(s.type == SpanType.BOLD for s in spans)
    assert any(s.type == SpanType.ITALIC for s in spans)
