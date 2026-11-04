"""Source facts use short, project-authored fixtures; no third-party charts/lyrics."""
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
import urllib.error
import urllib.request
from email.message import Message

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import online_sources as sources


HOUSE = "https://richterguitar.com/house-of-the-rising-sun-the-animals/"
WILD = "https://www.laurenbateman.com/wild-thing-chord-chart/"
DYLAN = "https://songnotes.net/lessons/88/"
WONDER = "https://www.martyschwartzguitar.com/wonderwall-by-oasis-easy-guitar-lesson-marty-schwartz/"


def page(title, artist, content, container="article"):
    return f"<html><title>{title} | {artist}</title><{container}><h1>{title}</h1><p>{artist} lesson.</p>{content}</{container}></html>"


class FactExtractionTests(unittest.TestCase):
    def test_house_two_source_intro_facts_and_optional_vocabulary(self):
        # Both public teachers describe this same short introductory order.
        body = "<h2>Intro</h2><p>Am C D F<br>Am E Am E</p><p>Optional chord E7.</p>"
        result = sources.extract_source(page("House of the Rising Sun", "The Animals", body), HOUSE,
                                        "House of the Rising Sun", "The Animals")
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["ordered_sections"], [{"name": "intro", "chords": ["Am", "C", "D", "F", "Am", "E", "Am", "E"]}])
        self.assertIn("E7", result["chord_shapes"])
        self.assertIsNone(result["capo"])
        self.assertIsNone(result["tuning_shift_semitones"])
        self.assertNotIn("excerpt", result)

    def test_house_explicit_intro_sentence(self):
        body = "<p>Intro progression goes as follows: Am, C, D, F, then Am, E, Am, E.</p>"
        result = sources.extract_source(page("House of the Rising Sun", "The Animals", body), HOUSE,
                                        "House of the Rising Sun", "The Animals")
        self.assertEqual(len(result["ordered_sections"][0]["chords"]), 8)

    def test_div_lesson_body_can_establish_artist_with_exact_house_target(self):
        # Jon's lesson uses a scoped div rather than article/main landmarks.
        text = "<html><title>The ULTIMATE House of the Rising Sun Guitar Lesson</title><div id='section-blog_post_body'><p>The Animals lesson.</p><p>Intro progression goes as follows: Am, C, D, F, then Am, E, Am, E.</p></div></html>"
        url = "https://www.jonmaclennan.com/blog/house-of-the-rising-sun-guitar-lesson"
        result = sources.extract_source(text, url, "The House Of The Rising Sun", "The Animals")
        self.assertEqual(result["identity"], {"song_title_matches": True, "artist_matches": True})
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(len(result["ordered_sections"][0]["chords"]), 8)

    def test_wild_riff_and_power_chords_preserved_without_strum_counts(self):
        body = "<p>Full chords A, D and E or power chords A5, D5 and E5.</p><p>Little riff: G A G A (hold)</p><p>AA DD EE DDD</p>"
        result = sources.extract_source(page("Wild Thing", "The Troggs", body), WILD, "Wild Thing", "The Troggs")
        self.assertEqual(set(result["chord_shapes"]), {"A", "D", "E", "A5", "D5", "E5", "G"})
        self.assertEqual(result["ordered_sections"], [])

    def test_dylan_main_and_optional_am7_are_retained(self):
        body = "<p>Main chords: G, D, C and A minor.</p><p>Modify chords from A-minor to Am7.</p>"
        result = sources.extract_source(page("Knockin' on Heaven's Door", "Bob Dylan", body), DYLAN,
                                        "Knockin' on Heaven's Door", "Bob Dylan")
        self.assertEqual(set(result["chord_shapes"]), {"G", "D", "C", "Am", "Am7"})

    def test_wonderwall_extensions_capo_and_standard_setup(self):
        body = "<p>Capo: 2nd fret</p><p>Tuning: Standard</p><p>Verse chord shapes: Em7 → G → Dsus4 → A7sus4.</p><p>Chords: Cadd9, D/F#, Bm7b5.</p>"
        result = sources.extract_source(page("Wonderwall", "Oasis", body), WONDER, "Wonderwall", "Oasis")
        self.assertEqual(result["capo"], 2)
        self.assertEqual(result["tuning_shift_semitones"], 0)
        self.assertEqual(result["chord_shapes"], ["Em7", "G", "Dsus4", "A7sus4", "Cadd9", "D/F#", "Bm7b5"])

    def test_tuning_note_names_and_finger_instructions_do_not_become_chords(self):
        body = "<p>Chords: G, D, Am, C.</p><p>These chord shapes keep fingers on the E and B strings.</p><p>In these chords the high-E string rings over C and Am.</p><p>E A D G B E</p>"
        result = sources.extract_source(page("Knockin' on Heaven's Door", "Bob Dylan", body), DYLAN,
                                        "Knockin' on Heaven's Door", "Bob Dylan")
        self.assertEqual(result["chord_shapes"], ["G", "D", "Am", "C"])

    def test_wrong_artist_or_title_abstains(self):
        text = page("Wild Thing", "Jimi Hendrix", "<p>Chords: A, D, E.</p>")
        self.assertEqual(sources.extract_source(text, WILD, "Wild Thing", "The Troggs")["status"], "identity-mismatch")
        self.assertEqual(sources.extract_source(text, WILD, "Different Song", "Jimi Hendrix")["status"], "identity-mismatch")

    def test_artist_alias_apostrophes_and_stopwords(self):
        text = page("Knocking on Heavens Door", "Bob Dylan", "<p>Chords: G, D, Am, C.</p>")
        result = sources.extract_source(text, DYLAN, "Knockin' on Heaven's Door", "Dylan")
        self.assertEqual(result["status"], "extracted")

    def test_unknown_article_abstains_instead_of_scanning_page(self):
        text = "<html><title>Wild Thing The Troggs</title><div>Chords A D E</div></html>"
        self.assertEqual(sources.extract_source(text, WILD, "Wild Thing", "The Troggs")["status"], "unsupported")

    def test_navigation_comments_scripts_and_nested_articles_excluded(self):
        text = page("Wild Thing", "The Troggs", "<p>Chords: A, D, E.</p><div class='comments'><div class='entry-content'>Chords: Bm, F#m.</div></div><nav><article class='entry-content'>Chords: C, F.</article></nav><script>Chords: Cm, Fm.</script>")
        result = sources.extract_source(text, WILD, "Wild Thing", "The Troggs")
        self.assertEqual(result["chord_shapes"], ["A", "D", "E"])

    def test_theme_sidebar_body_flags_do_not_hide_lesson(self):
        text = page("Wild Thing", "The Troggs", "<p>Chords: A, D, E.</p>")
        text = text.replace("<article>", "<body class='ast-no-sidebar fl-has-sidebar'><article>").replace("</article>", "</article></body>")
        self.assertEqual(sources.extract_source(text, WILD, "Wild Thing", "The Troggs")["status"], "extracted")

    def test_numbered_course_title_needs_both_song_slug_and_short_summary(self):
        text = page("Beatles Day 1 - chords G C D", "The Beatles",
                    "<div class='content-video-text'><p>Learn Love Me Do.</p><p>G major: a grip</p><p>C major: a grip</p><p>D major: a grip</p><p>Cadd9: optional</p></div>", "main")
        url = "https://www.andyguitar.co.uk/videos/beatles-guitar-day-01-love-me-do"
        result = sources.extract_source(text, url, "Love Me Do", "The Beatles")
        self.assertEqual(result["status"], "extracted")
        self.assertEqual(result["chord_shapes"], ["G", "C", "D", "Cadd9"])
        wrong_slug = sources.extract_source(text, url.replace("love-me-do", "other-song"), "Love Me Do", "The Beatles")
        self.assertEqual(wrong_slug["status"], "identity-mismatch")

    def test_video_text_scope_excludes_transcript_and_course_navigation(self):
        text = page("Wild Thing", "The Troggs", "<p>Transcript: chords Bm F#m and notes.</p><div class='content-video-text'><p>A major: grip</p><p>D major: grip</p><p>E major: grip</p></div><p>Other course chords: C F G.</p>", "main")
        self.assertEqual(sources.extract_source(text, WILD, "Wild Thing", "The Troggs")["chord_shapes"], ["A", "D", "E"])

    def test_explicit_chord_list_allows_parenthetical_fret_descriptions(self):
        text = page("Creep", "Radiohead", "<p>The chords are G major (3rd fret), B major (7th fret), C major (8th fret), C minor (8th fret, lift a finger).</p>")
        url = "https://www.andyguitar.co.uk/videos/radiohead-creep"
        self.assertEqual(sources.extract_source(text, url, "Creep", "Radiohead")["chord_shapes"], ["G", "B", "C", "Cm"])

    def test_key_scale_and_chord_note_theory_is_not_teaching_palette(self):
        body = "<p>Main chords: D, G, A.</p><p>All chords fit the D major scale using notes D E F# G A B C#.</p><p>In this key, the diatonic chords are:</p><p>I (D major): D F# A</p><p>Scale degrees: 1 D, 3 F#, 5 A.</p><p>Optional variation on the A chord?</p><p>Well, it’s A7. Lift a finger from the string.</p>"
        text = page("Twist and Shout", "The Beatles", body)
        url = "https://www.jonmaclennan.com/blog/twist-and-shout-chords"
        self.assertEqual(sources.extract_source(text, url, "Twist and Shout", "The Beatles")["chord_shapes"], ["D", "G", "A", "A7"])

    def test_contradictory_capo_abstains(self):
        text = page("Wonderwall", "Oasis", "<p>Chords: Em7 G Dsus4 A7sus4.</p><p>Capo: 2nd fret.</p><p>Other lesson uses capo: 3rd fret.</p>")
        result = sources.extract_source(text, WONDER, "Wonderwall", "Oasis")
        self.assertEqual(result["status"], "ambiguous-setup")
        self.assertIsNone(result["capo"])

    def test_nonuniform_or_mixed_tuning_abstains(self):
        for setup in ["The tuning is Open A.", "D standard tuning in studio; E-flat standard live."]:
            text = page("Wild Thing", "The Troggs", "<p>Chords: A, D, E.</p><p>" + setup + "</p>")
            result = sources.extract_source(text, WILD, "Wild Thing", "The Troggs")
            self.assertEqual(result["status"], "ambiguous-setup")
            self.assertIsNone(result["tuning_shift_semitones"])

    def test_declared_uniform_detuning(self):
        text = page("Wild Thing", "The Troggs", "<p>Chords: A, D, E.</p><p>D standard tuning. No capo.</p>")
        result = sources.extract_source(text, WILD, "Wild Thing", "The Troggs")
        self.assertEqual(result["tuning_shift_semitones"], -2)
        self.assertEqual(result["capo"], 0)

    def test_explicit_variant_is_reported(self):
        result = sources.extract_source(page("Wild Thing fingerstyle", "The Troggs", "<p>Chords: A, D, E.</p>"),
                                        WILD + "fingerstyle/", "Wild Thing", "The Troggs")
        self.assertTrue(result["arrangement_variant"])

    def test_oversized_intro_is_not_persisted_as_chart(self):
        text = page("Wild Thing", "The Troggs", "<h2>Intro</h2><p>" + "A D E D " * 6 + "</p>")
        result = sources.extract_source(text, WILD, "Wild Thing", "The Troggs")
        self.assertEqual(result["ordered_sections"], [])

    def test_challenge_is_not_extracted(self):
        text = page("Wild Thing", "The Troggs", "<form id='anomaly-form'></form><script src='anomaly.js'></script>")
        self.assertEqual(sources.extract_source(text, WILD, "Wild Thing", "The Troggs")["status"], "fetch-failed")

    def test_deep_html_structure_abstains(self):
        text = page("Wild Thing", "The Troggs", "<div>" * 270 + "Chords A D E" + "</div>" * 270)
        self.assertEqual(sources.extract_source(text, WILD, "Wild Thing", "The Troggs")["status"], "unsupported")


class NetworkAndCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)

    def test_discovery_decodes_result_links_and_ignores_private_urls(self):
        html = b'<a rel="nofollow" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.laurenbateman.com%2Fwild-thing-chord-chart%2F&amp;rut=x">Lesson</a><a rel="nofollow" href="http://127.0.0.1/">bad</a>'
        with patch.object(sources, "_request", return_value=(html, sources.SEARCH_URL, "text/html")):
            result = sources.discover("Wild Thing Troggs chords", self.cache)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["urls"], [sources.canonical_url(WILD)])

    def test_search_challenge_reports_blocked_and_never_falls_back_to_bypass(self):
        with patch.object(sources, "_request", return_value=(b'<form id="challenge-form">anomaly.js</form>', sources.SEARCH_URL, "text/html")) as request:
            result = sources.discover("Wild Thing chords", self.cache)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["urls"], [])
        self.assertEqual(request.call_count, 1)

    def test_search_unknown_layout_is_failed_not_empty_success(self):
        with patch.object(sources, "_request", return_value=(b"<html>loading</html>", sources.SEARCH_URL, "text/html")):
            self.assertEqual(sources.discover("Wild Thing chords", self.cache)["status"], "failed")

    def test_search_rate_limit_is_blocked(self):
        error = urllib.error.HTTPError(sources.SEARCH_URL, 429, "limit", {}, io.BytesIO())
        with patch.object(sources, "_request", side_effect=error):
            self.assertEqual(sources.discover("Wild Thing chords", self.cache)["status"], "blocked")

    def test_discovery_cache_and_offline_miss(self):
        with patch.object(sources, "_request", return_value=(b"No results found", sources.SEARCH_URL, "text/html")) as request:
            result = sources.discover("Wild Thing chords", self.cache)
            again = sources.discover("Wild Thing chords", self.cache)
            offline = sources.discover("Wild Thing chords", self.cache, offline=True)
        self.assertEqual(request.call_count, 1)
        self.assertFalse(result["cache_hit"])
        self.assertTrue(again["cache_hit"])
        self.assertTrue(offline["cache_hit"])
        with patch.object(sources, "_request", side_effect=AssertionError("network forbidden")):
            self.assertIn("offline-cache-miss", sources.discover("other", self.cache, offline=True)["notes"])

    def test_stale_offline_discovery_abstains(self):
        cache_path = sources._cache_path(self.cache, "discovery", "query")
        sources._save(cache_path, {"status": "ok", "urls": [WILD]})
        raw = json.loads(cache_path.read_text())
        raw["cached_at_epoch"] = time.time() - sources.CACHE_TTL_SECONDS - 100
        cache_path.write_text(json.dumps(raw))
        with patch.object(sources, "_request", side_effect=AssertionError("network forbidden")):
            result = sources.discover("query", self.cache, offline=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["urls"], [])
        self.assertIn("offline-stale-cache", result["notes"])

    def test_source_cache_holds_derived_facts_only(self):
        body = page("Wild Thing", "The Troggs", "<p>Chords: A D E.</p><p>private lyric placeholder NEVER_STORE_THIS_TEXT</p>").encode()
        with patch.object(sources, "_robots", return_value=(True, "robots-allowed")), patch.object(sources, "_request", return_value=(body, WILD, "text/html")) as request:
            result = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache)
            again = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache, offline=True)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result["status"], "extracted")
        self.assertTrue(again["cache_hit"])
        self.assertFalse(any("NEVER_STORE_THIS_TEXT" in path.read_text() for path in self.cache.rglob("*.json")))
        self.assertTrue(result["content_sha256"])

    def test_offline_source_miss_and_stale_never_fetch(self):
        with patch.object(sources, "_request", side_effect=AssertionError("network forbidden")):
            result = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache, offline=True)
        self.assertEqual(result["status"], "fetch-failed")
        self.assertEqual(result["chord_shapes"], [])
        self.assertIn("offline-cache-miss", result["notes"])

    def test_old_parser_cache_is_not_reused_but_search_cache_stays_valid(self):
        url = sources.canonical_url(WILD)
        identity = json.dumps([url, "Wild Thing", "The Troggs"], ensure_ascii=True)
        path = sources._cache_path(self.cache, "sources", identity)
        sources._save(path, {"status": "extracted", "chord_shapes": ["Bm"], "parser_version": "old"})
        with patch.object(sources, "_request", side_effect=AssertionError("network forbidden")):
            result = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache, offline=True)
        self.assertEqual(result["status"], "fetch-failed")
        self.assertEqual(result["chord_shapes"], [])
        self.assertEqual(result["parser_version"], sources.PARSER_VERSION)

    def test_expired_offline_source_facts_are_not_reused(self):
        url = sources.canonical_url(WILD)
        identity = json.dumps([url, "Wild Thing", "The Troggs"], ensure_ascii=True)
        path = sources._cache_path(self.cache, "sources", identity)
        sources._save(path, {"status": "extracted", "chord_shapes": ["A", "D", "E"], "parser_version": sources.PARSER_VERSION})
        raw = json.loads(path.read_text())
        raw["cached_at_epoch"] = time.time() - sources.CACHE_TTL_SECONDS - 1
        path.write_text(json.dumps(raw))
        with patch.object(sources, "_request", side_effect=AssertionError("network forbidden")):
            result = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache, offline=True)
        self.assertEqual(result["status"], "fetch-failed")
        self.assertEqual(result["chord_shapes"], [])
        self.assertIn("offline-stale-cache", result["notes"])

    def test_unsupported_private_domains_ports_and_pdf_never_fetch(self):
        for url in ["https://127.0.0.1/", "https://localhost/", "http://laurenbateman.com/x", "https://laurenbateman.com:8080/x", "https://laurenbateman.com@evil.example/", "https://unknown.example/", "https://laurenbateman.com/x.pdf"]:
            with patch.object(sources, "_request", side_effect=AssertionError("network forbidden")):
                result = sources.fetch_source(url, "Wild Thing", "The Troggs", self.cache)
            self.assertEqual(result["status"], "unsupported", url)

    def test_redirect_outside_allowlist_and_to_private_host_is_rejected(self):
        handler = sources._SafeRedirect(sources.allowed_source_url)
        request = urllib.request.Request(WILD)
        for target in ["https://evil.example/", "https://127.0.0.1/", "http://laurenbateman.com/"]:
            with self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_response_limit_prevents_large_html(self):
        response = Mock()
        headers = Message()
        headers["Content-Type"] = "text/html"
        response.headers = headers
        response.geturl.return_value = WILD
        response.read.return_value = b"x" * 11
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        with patch("urllib.request.build_opener", return_value=opener), self.assertRaises(ValueError):
            sources._request(WILD, sources.allowed_source_url, 10)
        response.read.assert_called_once_with(11)

    def test_robots_disallow_is_respected(self):
        robots = b"User-agent: *\nDisallow: /wild-thing-chord-chart/\n"
        with patch.object(sources, "_request", return_value=(robots, "https://laurenbateman.com/robots.txt", "text/plain")) as request:
            result = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache)
        self.assertEqual(result["status"], "fetch-failed")
        self.assertTrue(any("robots-disallow" in note for note in result["notes"]))
        self.assertEqual(request.call_count, 1)

    def test_robots_unavailable_abstains_without_source_fetch(self):
        with patch.object(sources, "_request", side_effect=OSError("network")) as request:
            result = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache)
        self.assertEqual(result["status"], "fetch-failed")
        self.assertEqual(request.call_count, 1)

    def test_robots_missing_is_not_a_disallow(self):
        error = urllib.error.HTTPError("https://laurenbateman.com/robots.txt", 404, "missing", {}, io.BytesIO())
        with patch.object(sources, "_request", side_effect=error):
            allowed, note = sources._robots(sources.canonical_url(WILD), self.cache)
        self.assertTrue(allowed)
        self.assertEqual(note, "robots-not-present")

    def test_source_failure_records_http_status(self):
        error = urllib.error.HTTPError(WILD, 429, "limit", {}, io.BytesIO())
        with patch.object(sources, "_robots", return_value=(True, "robots-allowed")), patch.object(sources, "_request", side_effect=error):
            result = sources.fetch_source(WILD, "Wild Thing", "The Troggs", self.cache)
        self.assertEqual(result["status"], "fetch-failed")
        self.assertIn("HTTP 429", " ".join(result["notes"]))

    def test_canonical_identity_removes_trackers_www_and_fragment(self):
        self.assertEqual(sources.canonical_url(WILD + "?utm_source=x#part"), "https://laurenbateman.com/wild-thing-chord-chart/")
        self.assertTrue(sources.allowed_source_url(WONDER))
        self.assertFalse(sources.allowed_source_url("https://fake.laurenbateman.com/"))


if __name__ == "__main__":
    unittest.main()
