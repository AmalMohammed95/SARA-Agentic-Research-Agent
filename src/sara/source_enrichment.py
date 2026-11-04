"""Opt-in bounded open-access text enrichment, without arbitrary URL fetching.

Only arXiv HTML and Europe PMC open-access XML are retrieved. Missing text
remains missing; the abstract is never represented as a full paper.
"""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HOSTS = frozenset(('arxiv.org', 'ar5iv.labs.arxiv.org', 'www.ebi.ac.uk'))
MAX_BYTES = 1_500_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname not in HOSTS:
            raise ValueError('Unapproved redirect')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def _fetch(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password:
        raise ValueError('Unapproved URL')
    request = urllib.request.Request(url, headers={'User-Agent': 'SARA-Academic-Research-Agent/1.0'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=5) as reply:
        if urllib.parse.urlsplit(reply.geturl()).hostname not in HOSTS:
            raise ValueError('Unapproved response URL')
        length = reply.headers.get('Content-Length')
        if length and int(length) > MAX_BYTES:
            raise ValueError('Payload size exceeded')
        body = reply.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Payload size exceeded')
        return body


class ArticleHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'footer', 'svg', 'header'):
            self.skip.append(tag)
        elif not self.skip and tag in ('p', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.skip and self.skip[-1] == tag:
            self.skip.pop()
        elif not self.skip and tag in ('p', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data + ' ')


def _clean(value):
    return '\n'.join(' '.join(x.split()) for x in value.splitlines() if x.strip())[:90000]


def _extract_html(raw):
    parser = ArticleHTML()
    parser.feed(raw.decode('utf-8', errors='replace'))
    return _clean(''.join(parser.parts))


def _extract_xml(raw):
    root = ET.fromstring(raw)
    parts = []
    for item in root.iter():
        tag = item.tag.split('}')[-1]
        if tag in ('p', 'title', 'abstract'):
            t = ' '.join(''.join(item.itertext()).split())
            if len(t) >= 20:
                parts.append(t)
    return _clean('\n'.join(parts))


def obtain_open_text(paper, fetch=_fetch):
    """Return provenance, or a truthful abstract-only fallback."""
    abst = str(paper.get('abstract') or '')
    identifier = ' '.join(str(paper.get(k) or '') for k in ('doi', 'id'))
    match = re.search(r'(?:arxiv[./]|arxiv\.org/(?:abs|html)/)(\d{4}\.\d{4,5})(?:v\d+)?', identifier, re.I)
    if match:
        arxiv_id = match.group(1)
        urls = (f'https://arxiv.org/html/{arxiv_id}', f'https://ar5iv.labs.arxiv.org/html/{arxiv_id}')
        for url in urls:
            try:
                text = _extract_html(fetch(url))
                if len(text) >= max(1000, len(abst) + 250):
                    return {'text': text, 'source_url': url, 'source_scope': 'open_access_full_text'}
            except (OSError, ValueError, TimeoutError, UnicodeError):
                continue
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:)', '', str(paper.get('doi') or ''), flags=re.I)
    if re.fullmatch(r'10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+', doi):
        url = ('https://www.ebi.ac.uk/europepmc/webservices/rest/search?'
               + urllib.parse.urlencode({'query': 'DOI:' + doi, 'format': 'json', 'pageSize': 1}))
        try:
            obj = json.loads(fetch(url).decode('utf-8'))
            results = obj.get('resultList', {}).get('result', [])
            pmcid = next((r.get('pmcid') for r in results if r.get('pmcid') and
                          str(r.get('isOpenAccess') or '').upper() == 'Y'), None)
            if pmcid and re.fullmatch(r'PMC\d+', pmcid):
                text_url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
                text = _extract_xml(fetch(text_url))
                if len(text) >= max(1000, len(abst) + 250):
                    return {'text': text, 'source_url': text_url, 'source_scope': 'open_access_full_text'}
        except (OSError, ValueError, TimeoutError, TypeError, KeyError, ET.ParseError, UnicodeError):
            pass
    return {'source_scope': 'abstract_only', 'source_url': None}


def enrich_papers(papers, *, max_papers=24, fetch=_fetch):
    work = [dict(p) for p in papers]
    n = min(max_papers, len(work))
    if n == 0:
        return work
    with ThreadPoolExecutor(max_workers=min(4, n)) as pool:
        futures = [pool.submit(obtain_open_text, paper, fetch) for paper in work[:n]]
        for paper, future in zip(work[:n], futures):
            try:
                item = future.result()
            except (OSError, ValueError, RuntimeError, TimeoutError):
                item = {'source_scope': 'abstract_only', 'source_url': None}
            paper['original_abstract'] = paper.get('abstract', '')
            paper['source_scope'] = item['source_scope']
            paper['source_url'] = item.get('source_url')
            if item.get('text'):
                paper['abstract'] = item['text']
    return work
