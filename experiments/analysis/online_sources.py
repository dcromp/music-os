"""Bounded public teacher-source discovery and derived chord facts.

The network stage stores result URLs and derived musical facts, never page HTML,
lyrics, tablature or complete charts. A teaching palette is incomplete evidence
about a lesson, not a transcription or an authority to change audio timings.
Only the standard library is required. The no-key discovery endpoint may block
automation; a challenge is reported rather than bypassed.
"""
from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import tempfile
import time
from datetime import datetime, timezone
from typing import Callable
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser


ALLOWED_DOMAINS = frozenset({
    "andyguitar.co.uk", "guitarlessons365.com", "laurenbateman.com",
    "jonmaclennan.com", "songnotes.net", "goodguitarist.com",
    "richterguitar.com", "justinguitar.com", "martyschwartzguitar.com",
    "simpleguitar.com",
})
PROVIDER = "duckduckgo-lite"
SEARCH_URL = "https://lite.duckduckgo.com/lite/"
USER_AGENT = "music-os-source-review/1.0 (+https://github.com/dcromp/music-os)"
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
FAILURE_TTL_SECONDS = 60 * 60
TIMEOUT_SECONDS = 12
MAX_HTML_BYTES = 2_000_000
MAX_SEARCH_BYTES = 350_000
MAX_ROBOTS_BYTES = 128_000
MAX_RESULTS = 12
MAX_INTRO_CHORDS = 16
_CACHE_VERSION = "online-sources-1.0"
PARSER_VERSION = "online-source-facts-1.2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _origin(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")


def canonical_url(url: str) -> str:
    """Canonical HTTPS URL; no credentials, unusual ports, fragments or trackers."""
    if not isinstance(url, str) or len(url) > 4096:
        raise ValueError("Invalid URL")
    parsed = urllib.parse.urlsplit(html.unescape(url.strip()))
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid URL port") from exc
    if (parsed.scheme.lower() != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or port not in (None, 443)):
        raise ValueError("Only credential-free HTTPS URLs on the default port are supported")
    hostname = parsed.hostname.lower().rstrip(".").removeprefix("www.")
    if hostname in {"localhost", "localhost.localdomain"}:
        raise ValueError("Private hosts are not supported")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("IP-address source URLs are not supported")
    path = urllib.parse.quote(urllib.parse.unquote(parsed.path or "/"),
                              safe="/:@-._~!$&'()*+,;=")
    query = urllib.parse.urlencode([
        (key, value) for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ])
    return urllib.parse.urlunsplit(("https", hostname, path, query, ""))


def allowed_source_url(url: str) -> bool:
    try:
        clean = canonical_url(url)
    except (TypeError, ValueError):
        return False
    return _origin(clean) in ALLOWED_DOMAINS


def _search_allowed(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(canonical_url(url))
    except (TypeError, ValueError):
        return False
    return parsed.hostname == "lite.duckduckgo.com" and parsed.path.startswith("/lite")


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 2

    def __init__(self, allowed: Callable[[str], bool]):
        self.allowed = allowed

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not self.allowed(newurl):
            raise ValueError("Redirect outside allowed HTTPS source domains")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request(url: str, allowed: Callable[[str], bool], maximum: int) -> tuple[bytes, str, str]:
    if not allowed(url):
        raise ValueError("URL outside allowed HTTPS domains")
    opener = urllib.request.build_opener(_SafeRedirect(allowed))
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        if not allowed(final_url):
            raise ValueError("Final URL outside allowed HTTPS domains")
        length = response.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > maximum:
            raise ValueError("Response exceeds bounded size")
        data = response.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("Response exceeds bounded size")
        content_type = response.headers.get_content_type()
        return data, final_url, content_type


def _cache_path(cache_dir: Path | str, kind: str, identity: str) -> Path:
    key = hashlib.sha256((_CACHE_VERSION + "\n" + identity).encode()).hexdigest()
    return Path(cache_dir) / kind / (key + ".json")


def _cached(path: Path, ttl: int) -> tuple[dict | None, bool]:
    try:
        if path.is_symlink() or path.stat().st_size > MAX_HTML_BYTES:
            return None, False
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("cache_version") != _CACHE_VERSION or not isinstance(value.get("document"), dict):
            return None, False
        age = time.time() - float(value["cached_at_epoch"])
        return value["document"], 0 <= age <= ttl
    except (OSError, ValueError, TypeError, KeyError):
        return None, False


def _save(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cache_version": _CACHE_VERSION, "cached_at_epoch": time.time(), "document": document}
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".source-cache-", delete=False) as output:
        temporary = Path(output.name)
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
    temporary.replace(path)


def _challenge(page: str) -> bool:
    lower = page.lower()
    return any(marker in lower for marker in (
        'id="challenge-form"', 'id="anomaly-form"', "anomaly.js", "cf-chl-",
        "verify you are human", "checking your browser", "captcha-delivery.com",
    ))


class _SearchLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag != "a" or "nofollow" not in attributes.get("rel", "").split():
            return
        raw = attributes.get("href", "")
        absolute = urllib.parse.urljoin(SEARCH_URL, raw)
        parsed = urllib.parse.urlsplit(absolute)
        if parsed.hostname in {"duckduckgo.com", "www.duckduckgo.com"} and parsed.path == "/l/":
            target = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
        else:
            target = absolute
        try:
            clean = canonical_url(target)
        except ValueError:
            return
        if clean not in self.urls and len(self.urls) < MAX_RESULTS:
            self.urls.append(clean)


def discover(query: str, cache_dir: Path | str, refresh: bool = False,
             offline: bool = False) -> dict:
    """Discover public result URLs; challenge/failed never means no matching song."""
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError("Use a nonempty search query of at most 500 characters")
    query = " ".join(query.split())
    path = _cache_path(cache_dir, "discovery", query)
    cached, fresh = _cached(path, CACHE_TTL_SECONDS)
    if cached and cached.get("status") != "ok":
        _, fresh = _cached(path, FAILURE_TTL_SECONDS)
    if cached and fresh and (offline or not refresh):
        return {**cached, "cache_hit": True}
    base = {"provider": PROVIDER, "status": "failed", "query": query, "urls": [],
            "retrieved_at_utc": _now(), "cache_hit": False, "notes": []}
    if offline:
        base["notes"] = ["offline-stale-cache" if cached else "offline-cache-miss"]
        return base
    try:
        request_url = SEARCH_URL + "?" + urllib.parse.urlencode({"q": query})
        body, final_url, content_type = _request(request_url, _search_allowed, MAX_SEARCH_BYTES)
        page = body.decode("utf-8", errors="replace")
        base.update({"request_url": request_url, "response_url": final_url,
                     "content_sha256": hashlib.sha256(body).hexdigest()})
        if _challenge(page):
            base.update(status="blocked", notes=["search-provider-challenge; no bypass attempted"])
        elif content_type not in {"text/html", "application/xhtml+xml"}:
            base["notes"] = ["unsupported-search-content-type"]
        else:
            parser = _SearchLinks()
            parser.feed(page)
            # A real empty-results page has an explicit no-results indication.
            if parser.urls or re.search(r"no (?:more )?results|no results found", page, re.I):
                base.update(status="ok", urls=parser.urls)
            else:
                base["notes"] = ["unrecognised-search-response; no result count inferred"]
    except (OSError, ValueError, urllib.error.URLError) as exc:
        code = getattr(exc, "code", None)
        base["status"] = "blocked" if code in {403, 429} else "failed"
        base["notes"] = ["search-fetch-failed: " + type(exc).__name__ + (" HTTP " + str(code) if code else "")]
    _save(path, base)
    return base


class _Node:
    def __init__(self, tag: str, attrs: dict | None = None, parent: _Node | None = None):
        self.tag = tag
        self.attrs = attrs or {}
        self.parent = parent
        self.children: list[_Node | str] = []


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "aside", "form", "button", "svg", "template"}
_BLOCK_TAGS = {"p", "div", "section", "article", "main", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "li", "blockquote", "table", "tr"}
_SKIP_MARKERS = re.compile(r"(?:^|[-_\s])(?:comments?|related|sidebar|navigation|newsletter|subscribe)(?:$|[-_\s])", re.I)


class _Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("document")
        self.stack = [self.root]
        self.nodes: list[_Node] = []

    def handle_starttag(self, tag, attrs):
        if len(self.nodes) > 150_000 or len(self.stack) > 256:
            raise ValueError("Lesson HTML exceeds bounded structure")
        node = _Node(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for position in range(len(self.stack) - 1, 0, -1):
            if self.stack[position].tag == tag:
                del self.stack[position:]
                break

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def _skip(node: _Node) -> bool:
    # Theme flags such as body.ast-no-sidebar / body.fl-has-sidebar describe
    # page layout; they are not the actual sidebar subtree.
    if node.tag in {"document", "html", "body"}:
        return False
    marker = node.attrs.get("class", "") + " " + node.attrs.get("id", "")
    return node.tag in _SKIP_TAGS or bool(_SKIP_MARKERS.search(marker))


def _visible(node: _Node) -> bool:
    while node is not None:
        if _skip(node):
            return False
        node = node.parent
    return True


def _text(node: _Node, lines: bool = True) -> str:
    if _skip(node):
        return ""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        else:
            if lines and (child.tag in _BLOCK_TAGS or child.tag == "br"):
                parts.append("\n")
            parts.append(_text(child, lines))
            if lines and child.tag in _BLOCK_TAGS:
                parts.append("\n")
    return "".join(parts)


def _scope(document: _Document) -> _Node | None:
    ranked: list[tuple[int, int, _Node]] = []
    for node in document.nodes:
        marker = node.attrs.get("class", "") + " " + node.attrs.get("id", "")
        if not _visible(node):
            continue
        score = (5 if "content-video-text" in marker
                 else 4 if re.search(r"entry-content|fl-post-content|article[-_]body|blog[-_]post[-_]body|post[-_]content", marker)
                 or node.attrs.get("itemprop") in {"articleBody", "text"}
                 else 3 if node.tag == "article" else 2 if node.tag == "main" else 0)
        if score:
            size = len(_text(node))
            if size >= 15:
                ranked.append((score, size, node))
    return max(ranked, key=lambda row: (row[0], row[1]))[2] if ranked else None


def _words(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", plain)
    aliases = {"knocking": "knockin", "heavens": "heaven"}
    stops = {"the", "a", "an", "of", "on", "in", "and", "s", "by", "lesson", "chords", "guitar", "how", "to", "play"}
    return {aliases.get(word, word) for word in words if word not in stops}


_CHORD = re.compile(r"(?<![A-Za-z0-9#b])([A-G](?:#|b)?(?:(?:maj|min|dim|aug|sus|add|m|M)(?:\d+)?|\d+)?(?:sus\d+|add\d+|b\d+|#\d+)*(?:/[A-G](?:#|b)?)?)(?![A-Za-z0-9#/])")


def _normalise_chord_text(text: str) -> str:
    text = text.replace("♯", "#").replace("♭", "b")
    text = re.sub(r"\b([A-G][#b]?)[ -]+minor\b", r"\1m", text, flags=re.I)
    text = re.sub(r"\b([A-G][#b]?)[ -]+major\b", r"\1", text, flags=re.I)
    return text


def _tokens(text: str) -> list[str]:
    return [match.group(1).replace("min", "m") for match in _CHORD.finditer(_normalise_chord_text(text))]


def _chord_line(line: str) -> list[str]:
    clean = _normalise_chord_text(line)
    clean = re.sub(r"\((?:hold|repeat|x\s*\d+)\)", "", clean, flags=re.I)
    matches = list(_CHORD.finditer(clean))
    residual = _CHORD.sub("", clean)
    # Exclude lyrics, tab, counts, stroke symbols, explanations and note tuning.
    if (2 <= len(matches) <= MAX_INTRO_CHORDS
            and re.fullmatch(r"[\s,|:;\[\]{}()→–—\-•·/]*", residual)
            and [match.group(1) for match in matches] != ["E", "A", "D", "G", "B", "E"]):
        return [match.group(1).replace("min", "m") for match in matches]
    return []


def _setup(lines: list[str]) -> tuple[int | None, int | None, list[str], bool]:
    capos: set[int] = set()
    tuning: set[int] = set()
    notes: list[str] = []
    alternate = False
    for index, line in enumerate(lines):
        lower = line.lower()
        if re.search(r"\b(?:no capo|capo\s*:\s*none|without (?:a )?capo)\b", lower):
            capos.add(0)
        if lower.strip(" :") == "capo" and index + 1 < len(lines) and lines[index + 1].lower() in {"none", "no", "0"}:
            capos.add(0)
        for match in re.finditer(r"\bcapo(?:\s+(?:at|on|is|the|a|placed|positioned|fret|position))?\s*[:=]?\s*(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?(?:\s+fret)?\b", lower):
            value = int(match.group(1))
            if value <= 12:
                capos.add(value)
        if re.search(r"\b(?:standard tuning|tuning\s*:\s*standard|standard[- ]tuned|standard tuned guitar|e\s*[, -]\s*a\s*[, -]\s*d\s*[, -]\s*g\s*[, -]\s*b\s*[, -]\s*e)\b", lower):
            # 'D standard tuning' and 'Eb standard tuning' are not E standard.
            if not re.search(r"\b(?:d|eb|e-flat|e flat|d#)\s+standard", lower):
                tuning.add(0)
        if re.search(r"\b(?:d standard|whole[- ]step down|whole tone down|down (?:a |one )?(?:whole )?(?:step|tone))\b", lower):
            tuning.add(-2)
        if re.search(r"\b(?:e[- ]?flat standard|eb standard|half[- ]step down|semitone down|down (?:a |one )?half[- ]step)\b", lower):
            tuning.add(-1)
        if re.search(r"\b(?:open [a-g]|drop [a-g]|dadgad)\b", lower) and re.search(r"tun(?:e|ed|ing)", lower):
            alternate = True
    if len(capos) > 1:
        notes.append("conflicting-capo-statements; setup abstained")
    if len(tuning) > 1 or alternate:
        notes.append("mixed-or-nonuniform-tuning-statements; setup abstained")
    ambiguous = len(capos) > 1 or len(tuning) > 1 or alternate
    capo = next(iter(capos)) if len(capos) == 1 else None
    shift = next(iter(tuning)) if len(tuning) == 1 and not alternate else None
    if capo is None:
        notes.append("capo-not-explicitly-established")
    if shift is None:
        notes.append("uniform-tuning-shift-not-explicitly-established")
    return capo, shift, notes, ambiguous


def _base_source(url: str, title: str, artist: str) -> dict:
    return {"id": "source-" + hashlib.sha256(url.encode()).hexdigest()[:24],
            "title": title, "song_title": title, "artist": artist, "url": url,
            "origin_group": _origin(url), "status": "unsupported",
            "retrieved_at_utc": _now(), "content_sha256": None,
            "chord_shapes": [], "capo": None, "tuning_shift_semitones": None,
            "label_basis": "played-shapes", "scope": "teaching-palette",
            "ordered_sections": [], "arrangement_variant": False, "notes": [],
            "cache_hit": False, "parser_version": PARSER_VERSION}


def extract_source(page: str, url: str, title: str, artist: str,
                   content_sha256: str | None = None) -> dict:
    """Extract bounded facts from a public lesson article, with no retained prose."""
    url = canonical_url(url)
    result = _base_source(url, title, artist)
    result["content_sha256"] = content_sha256 or hashlib.sha256(page.encode()).hexdigest()
    if not allowed_source_url(url):
        result["notes"] = ["source-domain-not-allowlisted"]
        return result
    if _challenge(page):
        result.update(status="fetch-failed", notes=["source-challenge; no bypass attempted"])
        return result
    document = _Document()
    try:
        document.feed(page)
    except ValueError:
        result["notes"] = ["lesson-html-structure-exceeds-bounds"]
        return result
    scope = _scope(document)
    if scope is None:
        result["notes"] = ["no-recognised-lesson-article-scope"]
        return result
    headings = [_text(node, False).strip() for node in document.nodes
                if node.tag in {"title", "h1"} and _visible(node)]
    lesson_title = next((heading for heading in headings if _words(title) <= _words(heading)), "")
    body = _text(scope)
    title_words, artist_words = _words(title), _words(artist)
    title_match = bool(title_words and lesson_title)
    # Some course pages use a numbered lesson title. Require both the exact
    # song slug and a short visible lesson summary, not a navigation hit.
    slug_match = bool(title_words and title_words <= _words(urllib.parse.urlsplit(url).path))
    short_summary_match = any(title_words <= _words(line) for line in body.splitlines()
                              if 0 < len(line) <= 500)
    if not title_match and slug_match and short_summary_match:
        title_match = True
        lesson_title = next((heading for heading in headings if heading), title)
        result["notes"].append("song-title-established-by-slug-and-short-lesson-summary")
    identity_text = " ".join(_text(node) for node in document.nodes
                             if node.tag in {"article", "main"} and _visible(node))
    artist_match = bool(artist_words and artist_words <= _words(body + " " + identity_text + " " + " ".join(headings)))
    result["identity"] = {"song_title_matches": title_match, "artist_matches": artist_match}
    if not title_match or not artist_match:
        result.update(status="identity-mismatch", notes=["song-title-or-artist-not-established-in-lesson"])
        return result
    result["title"] = lesson_title[:300]
    variant_text = url + " " + lesson_title
    result["arrangement_variant"] = bool(re.search(r"fingerstyle|acoustic[- ]cover|live[- ](?:version|cover)|ukulele", variant_text, re.I))
    lines = [" ".join(line.split()) for line in body.splitlines() if line.strip()]
    vocabulary: list[str] = []
    intro: list[str] = []
    in_intro = False
    previous_variant = False
    for line in lines:
        chord_line = _chord_line(line)
        # A prose chord list is accepted only when it explicitly describes
        # lesson chords/shapes/notes, not arbitrary isolated capital letters.
        explicit_marker = re.search(r"\b(?:chords?|shapes?)(?:\s+they)?\s*(?:are|:)\s*", line, re.I)
        fact_line = re.sub(r"\([^()]{0,160}\)", "", line) if explicit_marker else line
        theory_notes = bool(re.search(r"\b(?:scale|diatonic|notes\s*:|scale degrees|function\s*:)\b", line, re.I))
        explicit_list = bool(len(line) <= 1200 and not theory_notes
                             and re.search(r"\b(?:chords?|shapes?|riff|progression)\b", fact_line, re.I)
                             and (re.search(r"\b(?:are|uses?|using|played|play|need|goes|follows|based|notes|shapes|chords)\b", line, re.I)
                                  or re.search(r"\b(?:chords?|shapes?|riff|progression)\s*:", line, re.I))
                             and not re.search(r"\b(?:strings?|frets?|fingers?|notes? in|notes?:|function:)\b", fact_line, re.I))
        chord_facts = chord_line or (_tokens(fact_line) if explicit_list else [])
        # Teacher chord lists often render one labeled grip per list item.
        label = re.match(r"^([A-G][#b]?(?:\s+(?:major|minor)|(?:m|maj|sus|add)?\d*(?:sus\d+|add\d+)?)?)\s*:", line)
        if label and not theory_notes:
            for chord in _tokens(label.group(1)):
                if chord not in vocabulary:
                    vocabulary.append(chord)
        if previous_variant:
            first_sentence = re.split(r"[.!?]", line, maxsplit=1)[0]
            variant_tokens = _tokens(first_sentence)
            if 1 <= len(variant_tokens) <= 2 and len(first_sentence) <= 100:
                for chord in variant_tokens:
                    if chord not in vocabulary:
                        vocabulary.append(chord)
        previous_variant = bool(len(line) <= 500 and re.search(r"\b(?:variation|optional|embellish|modify)\b.*\bchords?\b", line, re.I))
        named = re.search(r"\b(?:new|optional|final|last) chord\s+([A-G][#b]?(?:m|maj|sus|add)?\d*(?:sus\d+|add\d+)?)\b", line, re.I)
        if named and named.group(1) not in vocabulary:
            vocabulary.append(named.group(1))
        if 2 <= len(chord_facts) <= 32:
            for chord in chord_facts:
                if chord not in vocabulary:
                    vocabulary.append(chord)
        # Keep one short introductory sequence, never the full page chart.
        if not intro and re.search(r"\bintro\b", line, re.I) and "follows:" in line.lower():
            candidate = _tokens(re.split(r"follows:\s*", line, flags=re.I)[-1])
            if 2 <= len(candidate) <= MAX_INTRO_CHORDS:
                intro = candidate
        if re.fullmatch(r"\[?(?:intro|introduction)\]?:?", line, re.I):
            in_intro = not intro
            continue
        if in_intro:
            if chord_line and len(intro) + len(chord_line) <= MAX_INTRO_CHORDS:
                intro.extend(chord_line)
            else:
                in_intro = False
    capo, tuning, setup_notes, ambiguous = _setup(lines)
    result.update(chord_shapes=vocabulary, capo=capo, tuning_shift_semitones=tuning,
                  ordered_sections=[{"name": "intro", "chords": intro}] if intro else [],
                  notes=result["notes"] + setup_notes + ["incomplete-teaching-vocabulary; may include optional variants",
                                      "no-recording-timestamps-or-full-arrangement-inferred"],
                  status="ambiguous-setup" if ambiguous else "extracted" if vocabulary else "unsupported")
    if result["arrangement_variant"]:
        result["notes"].append("explicit-arrangement-variant; exclude from main-recording consensus")
    if not vocabulary:
        result["notes"].append("no-explicit-chord-vocabulary-extracted")
    return result


def _robots(url: str, cache_dir: Path | str) -> tuple[bool, str]:
    parsed = urllib.parse.urlsplit(url)
    robots_url = urllib.parse.urlunsplit(("https", parsed.netloc, "/robots.txt", "", ""))
    path = _cache_path(cache_dir, "robots", robots_url)
    cached, fresh = _cached(path, CACHE_TTL_SECONDS)
    if not cached or not fresh:
        try:
            data, _, _ = _request(robots_url, allowed_source_url, MAX_ROBOTS_BYTES)
            cached = {"status": "ok", "text": data.decode("utf-8", errors="replace")}
        except urllib.error.HTTPError as exc:
            cached = {"status": "missing" if exc.code in {404, 410} else "unavailable", "text": ""}
        except (OSError, ValueError, urllib.error.URLError):
            cached = {"status": "unavailable", "text": ""}
        _save(path, cached)
    if cached["status"] == "missing":
        return True, "robots-not-present"
    if cached["status"] != "ok":
        return False, "robots-unavailable; source fetch abstained"
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(cached["text"].splitlines())
    if not parser.can_fetch(USER_AGENT, url):
        return False, "robots-disallow; no bypass attempted"
    delay = parser.crawl_delay(USER_AGENT) or 0
    rate = parser.request_rate(USER_AGENT)
    if rate:
        delay = max(delay, rate.seconds / rate.requests)
    if delay > 2:
        return False, "robots-crawl-delay-exceeds-bounded-budget; source fetch abstained"
    if delay:
        time.sleep(delay)
    return True, "robots-allowed"


def fetch_source(url: str, title: str, artist: str, cache_dir: Path | str,
                 refresh: bool = False, offline: bool = False) -> dict:
    """Fetch one allowlisted teacher page and cache only derived musical facts."""
    try:
        url = canonical_url(url)
    except (ValueError, TypeError):
        result = _base_source("https://invalid.example/", title, artist)
        result.update(url=str(url)[:4096], notes=["invalid-or-private-source-url"])
        return result
    result = _base_source(url, title, artist)
    if not allowed_source_url(url):
        result["notes"] = ["source-domain-not-allowlisted"]
        return result
    if urllib.parse.urlsplit(url).path.lower().endswith(".pdf"):
        result["notes"] = ["pdf-source-not-supported-by-html-fact-extractor"]
        return result
    identity = json.dumps([url, title, artist], ensure_ascii=True)
    path = _cache_path(cache_dir, "sources", identity)
    cached, fresh = _cached(path, CACHE_TTL_SECONDS)
    if cached and cached.get("parser_version") != PARSER_VERSION:
        cached, fresh = None, False
    if cached and cached.get("status") in {"fetch-failed"}:
        _, fresh = _cached(path, FAILURE_TTL_SECONDS)
    if cached and fresh and (offline or not refresh):
        return {**cached, "cache_hit": True}
    if offline:
        result.update(status="fetch-failed", notes=["offline-stale-cache" if cached else "offline-cache-miss"])
        return result
    permitted, robots_note = _robots(url, cache_dir)
    if not permitted:
        result.update(status="fetch-failed", notes=[robots_note])
        _save(path, result)
        return result
    try:
        body, final_url, content_type = _request(url, allowed_source_url, MAX_HTML_BYTES)
        if content_type not in {"text/html", "application/xhtml+xml"}:
            result["notes"] = ["unsupported-source-content-type"]
        else:
            result = extract_source(body.decode("utf-8", errors="replace"), final_url, title, artist,
                                    hashlib.sha256(body).hexdigest())
            result["requested_url"] = url
            result["notes"].append(robots_note)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        code = getattr(exc, "code", None)
        result.update(status="fetch-failed", notes=["source-fetch-failed: " + type(exc).__name__
                                                     + (" HTTP " + str(code) if code else "")])
    _save(path, result)
    return result
