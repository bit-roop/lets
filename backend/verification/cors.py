"""Origin restriction for M5 responses.

Why this is a middleware and not a router setting
-------------------------------------------------
There is no router-level CORS in Starlette or FastAPI.  `Starlette.add_middleware`
does `user_middleware.insert(0, ...)` and `build_middleware_stack` wraps
`self.router` in reverse order, so every middleware wraps the WHOLE application.
An `APIRouter` has no per-route ASGI wrapper.  Endpoint-specific CORS therefore
cannot be expressed without touching the application object in backend/main.py.

The application currently runs CORSMiddleware with allow_origins=["*"] and
allow_credentials=True.  In that combination Starlette does not emit a literal
"*": `if self.allow_all_origins and self.allow_credentials: allow_explicit_origin(...)`
echoes the caller's Origin and sets Access-Control-Allow-Credentials: true, so any
origin gets credentialed read access.  That is acceptable for M4 responses, which
carry no extracted document content, but not for M5 responses, which do.

Because add_middleware inserts at position 0, a middleware added AFTER
CORSMiddleware becomes the OUTERMOST layer: it sees the response after
CORSMiddleware has written its headers, and can correct them.

This middleware touches only paths under the M5 prefix.  Every other response,
including all M4 and M3 endpoints, passes through byte-identical.  The existing
global CORS configuration is deliberately left exactly as it is: tightening it
would be an unrelated change to M4 behaviour.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import ALLOWED_ORIGINS, API_PREFIX


class VerificationCorsMiddleware:
    def __init__(self, app: ASGIApp, prefix: str = API_PREFIX, allowed_origins=None):
        self.app = app
        self.prefix = prefix
        self.allowed_origins = tuple(
            ALLOWED_ORIGINS if allowed_origins is None else allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith(self.prefix):
            await self.app(scope, receive, send)
            return

        origin = None
        for key, value in scope.get("headers", []):
            if key == b"origin":
                origin = value.decode("latin-1")
                break

        allowed = origin is None or origin in self.allowed_origins

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if origin is not None:
                    if allowed:
                        headers["access-control-allow-origin"] = origin
                        vary = headers.get("vary")
                        if not vary:
                            headers["vary"] = "Origin"
                        elif "origin" not in vary.lower():
                            headers["vary"] = vary + ", Origin"
                    else:
                        # Strip the permissive headers the global middleware added,
                        # so the browser refuses to hand the body to the caller.
                        del headers["access-control-allow-origin"]
                        del headers["access-control-allow-credentials"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
