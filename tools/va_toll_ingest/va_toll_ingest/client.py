from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def build_authenticated_url(base_url: str, token: str) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["token"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def fetch_csv(base_url: str, token: str, *, timeout: int = 30) -> str:
    request = Request(build_authenticated_url(base_url, token), method="GET")
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")
