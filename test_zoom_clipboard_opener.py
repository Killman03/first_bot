import unittest

from zoom_clipboard_opener import (
    extract_zoom_meeting_urls,
    is_official_zoom_host,
    normalize_zoom_meeting_url,
)


class ZoomUrlTests(unittest.TestCase):
    def test_accepts_zoom_subdomain_meeting_link(self) -> None:
        url = "https://us06web.zoom.us/j/85905875411?pwd=secret"
        self.assertEqual(normalize_zoom_meeting_url(url), url)

    def test_extracts_link_from_message(self) -> None:
        text = "Встреча: https://zoom.us/j/12345678901?pwd=abc. Заходите!"
        self.assertEqual(
            extract_zoom_meeting_urls(text),
            ["https://zoom.us/j/12345678901?pwd=abc"],
        )

    def test_rejects_lookalike_domain(self) -> None:
        self.assertFalse(is_official_zoom_host("zoom.us.example.com"))
        self.assertIsNone(
            normalize_zoom_meeting_url("https://zoom.us.example.com/j/12345678901")
        )

    def test_rejects_non_meeting_zoom_page(self) -> None:
        self.assertIsNone(normalize_zoom_meeting_url("https://zoom.us/pricing"))

    def test_rejects_credentials_and_unusual_port(self) -> None:
        self.assertIsNone(
            normalize_zoom_meeting_url("https://user@zoom.us/j/12345678901")
        )
        self.assertIsNone(
            normalize_zoom_meeting_url("https://zoom.us:444/j/12345678901")
        )

    def test_accepts_web_client_join_link(self) -> None:
        url = "https://zoom.us/wc/12345678901/join?fromPWA=1"
        self.assertEqual(normalize_zoom_meeting_url(url), url)


if __name__ == "__main__":
    unittest.main()
