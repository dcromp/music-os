import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab


class AudioRangeTests(unittest.TestCase):
    def request(self, path, header=None):
        handler = lab.BenchHandler.__new__(lab.BenchHandler)
        handler.path = "/demo/audio.wav"
        handler.headers = {"Range": header} if header else {}
        handler.translate_path = lambda _: str(path)
        handler.response_headers = {}
        handler.send_response = lambda status: setattr(handler, "status", status)
        handler.send_header = lambda key, value: handler.response_headers.update({key: value})
        handler.end_headers = lambda: None
        handler.send_error = lambda status, _: setattr(handler, "status", status)
        source = handler.send_head()
        output = io.BytesIO()
        if source:
            try:
                handler.copyfile(source, output)
            finally:
                source.close()
        return handler, output.getvalue()

    def test_valid_partial_range_and_lengths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            path.write_bytes(b"0123456789")
            handler, data = self.request(path, "bytes=2-4")
            self.assertEqual(handler.status, 206)
            self.assertEqual(data, b"234")
            self.assertEqual(handler.response_headers["Content-Range"], "bytes 2-4/10")
            self.assertEqual(handler.response_headers["Content-Length"], "3")

    def test_suffix_and_open_ended_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            path.write_bytes(b"0123456789")
            self.assertEqual(self.request(path, "bytes=-3")[1], b"789")
            self.assertEqual(self.request(path, "bytes=7-")[1], b"789")

    def test_unsatisfiable_range_is_not_full_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            path.write_bytes(b"0123456789")
            handler, data = self.request(path, "bytes=20-")
            self.assertEqual(handler.status, 416)
            self.assertEqual(handler.response_headers["Content-Range"], "bytes */10")
            self.assertEqual(data, b"")

    def test_regular_audio_get_advertises_range_support(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            path.write_bytes(b"0123456789")
            handler, data = self.request(path)
            self.assertEqual(handler.status, 200)
            self.assertEqual(data, b"0123456789")
            self.assertEqual(handler.response_headers["Accept-Ranges"], "bytes")


if __name__ == "__main__":
    unittest.main()
