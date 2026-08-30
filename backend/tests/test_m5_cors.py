"""Origin handling for M5 responses.

M5 responses carry information read out of an applicant's document; M4 and M3
responses do not. The application-wide CORS middleware is configured
``allow_origins=["*"]`` with ``allow_credentials=True``, which makes Starlette
echo the caller's Origin and grant credentialed access to anyone. That is left
exactly as it is for M4 and M3 -- changing it would be an unrelated change to
M4 behaviour -- and corrected for M5 paths only.

There is no router-level CORS in Starlette, so this is a middleware registered
after CORSMiddleware, which makes it the outermost layer and lets it correct
the headers CORSMiddleware wrote. These tests check that at runtime rather than
trusting the ordering argument.
"""

import unittest

from backend.tests import m5_support as support

ALLOWED = "http://localhost:5173"
ALLOWED_ALT = "http://127.0.0.1:5173"
DISALLOWED = "http://evil.example"

M5_PATH = "/api/verification/capabilities"
M4_PATH = "/api/documents/requirements"
M3_PATH = "/api/health"


class TestM5OriginRestriction(unittest.TestCase):

    def setUp(self):
        self.api = support.client(self)

    def test_allowed_origin_is_granted(self):
        response = self.api.get(M5_PATH, headers={"origin": ALLOWED})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), ALLOWED)

    def test_second_configured_origin_is_granted(self):
        response = self.api.get(M5_PATH, headers={"origin": ALLOWED_ALT})
        self.assertEqual(response.headers.get("access-control-allow-origin"),
                         ALLOWED_ALT)

    def test_allowed_origin_response_varies_on_origin(self):
        """Without Vary: Origin a shared cache could serve one origin's
        response to another."""
        response = self.api.get(M5_PATH, headers={"origin": ALLOWED})
        self.assertIn("origin", response.headers.get("vary", "").lower())

    def test_disallowed_origin_is_refused_the_headers(self):
        response = self.api.get(M5_PATH, headers={"origin": DISALLOWED})
        # The body is still produced -- this is a browser-side control -- but the
        # browser will not hand it to the caller without the header.
        self.assertIsNone(response.headers.get("access-control-allow-origin"))
        self.assertIsNone(response.headers.get("access-control-allow-credentials"))

    def test_disallowed_origin_never_gets_the_wildcard_either(self):
        response = self.api.get(M5_PATH, headers={"origin": DISALLOWED})
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "*")

    def test_no_origin_header_is_left_alone(self):
        """Same-origin requests, curl and the test client carry no Origin."""
        response = self.api.get(M5_PATH)
        self.assertEqual(response.status_code, 200)

    def test_records_endpoint_is_covered_too(self):
        response = self.api.get("/api/verification/records",
                                params={"application_id": "cors-app"},
                                headers={"origin": DISALLOWED})
        self.assertIsNone(response.headers.get("access-control-allow-origin"))


class TestM5Preflight(unittest.TestCase):

    def setUp(self):
        self.api = support.client(self)

    def _preflight(self, origin, method="POST"):
        return self.api.options("/api/verification/analyze", headers={
            "origin": origin,
            "access-control-request-method": method,
            "access-control-request-headers": "content-type",
        })

    def test_preflight_from_an_allowed_origin_is_granted(self):
        response = self._preflight(ALLOWED)
        self.assertEqual(response.headers.get("access-control-allow-origin"), ALLOWED)

    def test_preflight_from_a_disallowed_origin_is_refused(self):
        response = self._preflight(DISALLOWED)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))
        self.assertIsNone(response.headers.get("access-control-allow-credentials"))


class TestM3AndM4CorsUnchanged(unittest.TestCase):
    """The existing behaviour on non-M5 paths is deliberately preserved."""

    def setUp(self):
        self.api = support.client(self)

    def test_m4_requirements_still_echoes_any_origin(self):
        response = self.api.post(M4_PATH, json={"facts": support.PERSONA_B},
                                 headers={"origin": DISALLOWED})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"),
                         DISALLOWED)

    def test_m4_readiness_still_echoes_any_origin(self):
        response = self.api.get("/api/documents/readiness", params={
            "application_id": "cors-app", "facts": "{}"},
            headers={"origin": DISALLOWED})
        self.assertEqual(response.headers.get("access-control-allow-origin"),
                         DISALLOWED)

    def test_engine_and_health_routes_still_echo_any_origin(self):
        response = self.api.get(M3_PATH, headers={"origin": DISALLOWED})
        self.assertEqual(response.headers.get("access-control-allow-origin"),
                         DISALLOWED)

    def test_m4_preflight_is_unchanged(self):
        response = self.api.options(M4_PATH, headers={
            "origin": DISALLOWED,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        })
        self.assertEqual(response.headers.get("access-control-allow-origin"),
                         DISALLOWED)

    def test_the_middleware_is_scoped_by_path_not_by_method(self):
        """A non-M5 path must be untouched regardless of verb."""
        for path in (M3_PATH, "/api/catalogue"):
            response = self.api.get(path, headers={"origin": DISALLOWED})
            self.assertEqual(
                response.headers.get("access-control-allow-origin"), DISALLOWED,
                f"{path} was affected by the M5 origin restriction")


if __name__ == "__main__":
    unittest.main()
