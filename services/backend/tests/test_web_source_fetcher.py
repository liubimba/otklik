import httpx

from otklik_backend.sources.fetchers import SOURCE_CONTENT_LIMIT, WebPageSourceFetcher


def make_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_extracts_visible_body_text_without_markup():
    html = """
    <html>
      <head><style>.x { color: red; }</style></head>
      <body>
        <nav>Nav link</nav>
        <header>Site header</header>
        <script>console.log('noise')</script>
        <main>
          <h1>Hello</h1>
          <p>World of  content</p>
        </main>
        <footer>Site footer</footer>
        <noscript>No JS</noscript>
      </body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=html)

    fetcher = WebPageSourceFetcher(client=make_client(handler))

    result = await fetcher.fetch("https://example.com")

    assert "Hello" in result.content
    assert "World of content" in result.content
    assert "Nav link" not in result.content
    assert "Site header" not in result.content
    assert "Site footer" not in result.content
    assert "console.log" not in result.content
    assert "No JS" not in result.content
    assert "<" not in result.content


async def test_fetch_truncates_content_to_source_content_limit():
    long_text = "word " * 3000
    html = f"<html><body><p>{long_text}</p></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=html)

    fetcher = WebPageSourceFetcher(client=make_client(handler))

    result = await fetcher.fetch("https://example.com")

    assert len(result.content) == SOURCE_CONTENT_LIMIT
