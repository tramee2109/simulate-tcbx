"""Core HTTP client and authentication helpers for The20 Simulation SDK."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

import requests


class The20APIError(Exception):
    """Raised when the simulation API returns a non-2xx response or auth error."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Any = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.payload = payload

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.code is not None:
            parts.append(f"code={self.code}")
        return " | ".join(parts)


def _decode_jwt_user_id(token: str) -> Optional[int]:
    """Best-effort extraction of user_id from JWT payload without verification."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(b64).decode("utf-8"))
        uid = claims.get("user_id") or claims.get("userId") or claims.get("sub")
        return int(uid) if uid is not None else None
    except Exception:
        return None


class BaseClient:
    """Shared HTTP, JWT login/refresh, and session helpers for Spot & Futures clients."""

    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        username: str = "",
        password: str = "",
        token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        session_key: str = "",
        timeout: float = 10.0,
        auto_refresh: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.refresh_token = refresh_token
        self.session_key = session_key
        self.timeout = timeout
        self.auto_refresh = auto_refresh
        self.user_id: Optional[int] = _decode_jwt_user_id(token) if token else None
        self.http = requests.Session()

        if not self.token and self.username and self.password:
            self.login()

    @property
    def ws_base_url(self) -> str:
        parsed = urlparse(self.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urlunparse((scheme, parsed.netloc, parsed.path, "", "", "")).rstrip("/")

    def login(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate via `/api/v1/auth/login/trader` and store JWT tokens."""
        user = username or self.username
        pwd = password or self.password
        if not user or not pwd:
            raise The20APIError("username and password are required to login")

        url = f"{self.base_url}/api/v1/auth/login/trader"
        resp = self.http.post(url, json={"username": user, "password": pwd}, timeout=self.timeout)
        data = self._parse_response(resp)
        token = data.get("token") or data.get("access_token")
        if not token:
            raise The20APIError("login succeeded but no token was returned", status_code=resp.status_code, payload=data)

        self.token = token
        self.refresh_token = data.get("refresh_token") or self.refresh_token
        user_obj = data.get("user") if isinstance(data.get("user"), dict) else {}
        uid = user_obj.get("id") or data.get("user_id") or _decode_jwt_user_id(token)
        self.user_id = int(uid) if uid is not None else None
        return data

    def refresh(self) -> Dict[str, Any]:
        """Refresh access token, falling back to `login()` if refresh fails."""
        if not self.refresh_token:
            return self.login()

        url = f"{self.base_url}/api/v1/auth/refresh"
        resp = self.http.post(url, json={"refresh_token": self.refresh_token}, timeout=self.timeout)
        if resp.status_code != 200:
            return self.login()

        data = self._parse_response(resp)
        token = data.get("token") or data.get("access_token")
        if not token:
            return self.login()

        self.token = token
        self.refresh_token = data.get("refresh_token") or self.refresh_token
        self.user_id = self.user_id or _decode_jwt_user_id(token)
        return data

    def _require_session_key(self, session_key: Optional[str]) -> str:
        sk = session_key or self.session_key
        if not sk:
            raise The20APIError("session_key is required (pass it to the method or client constructor)")
        return sk

    def _headers(self, auth: bool = True) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _parse_response(self, resp: requests.Response) -> Any:
        try:
            data = resp.json()
        except Exception:
            data = {"message": resp.text}

        if resp.status_code >= 400:
            msg = data.get("error") or data.get("message") or data.get("msg") or resp.text
            code = data.get("code")
            raise The20APIError(str(msg), status_code=resp.status_code, code=code, payload=data)
        return data

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        auth: bool = True,
    ) -> Any:
        """Execute an HTTP request with automatic token refresh on 401."""
        if auth and not self.token:
            self.login()

        url = f"{self.base_url}{path}"
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        resp = self.http.request(
            method=method.upper(),
            url=url,
            params=clean_params,
            json=json_body,
            headers=self._headers(auth=auth),
            timeout=self.timeout,
        )

        if resp.status_code == 401 and auth and self.auto_refresh and (self.refresh_token or (self.username and self.password)):
            self.refresh()
            resp = self.http.request(
                method=method.upper(),
                url=url,
                params=clean_params,
                json=json_body,
                headers=self._headers(auth=auth),
                timeout=self.timeout,
            )

        return self._parse_response(resp)

    def get_sessions(self) -> Any:
        """List available simulation sessions."""
        return self.request("GET", "/api/v1/simulation/sessions")
