"""Tock calendar transport: isolated browser mocks, no live requests or DB calls."""
import asyncio
import json
import shutil
import subprocess
from unittest.mock import AsyncMock

import pytest

from laughtrack.foundation.infrastructure.http import playwright_browser as module
from laughtrack.foundation.infrastructure.http.playwright_browser import PlaywrightBrowser

URL = "https://www.exploretock.com/batsu-chicago/experience/1/show"
HTML = "<html>Public Tock storefront</html>"


@pytest.fixture
def browser_chain():
    browser = PlaywrightBrowser()
    page = AsyncMock()
    page.content.return_value = HTML
    page.evaluate.side_effect = ["123", {"status": 200, "contentType": "application/octet-stream", "data": [218, 186, 29, 0]}]
    context = AsyncMock()
    context.new_page.return_value = page
    engine = AsyncMock()
    engine.new_context.return_value = context
    browser._browser = engine
    browser._launch_if_needed_locked = AsyncMock()
    return browser, engine, context, page


@pytest.mark.asyncio
async def test_reuses_challenge_context_and_sticky_proxy(browser_chain, monkeypatch):
    browser, engine, context, page = browser_chain
    page.content.return_value = "<html>Just a moment...</html>"
    browser._wait_for_cloudflare_challenge = AsyncMock(return_value=page.content.return_value)
    browser._solve_cloudflare_if_stuck = AsyncMock(return_value=HTML)
    monkeypatch.setattr(module, "build_default_cloudflare_solver", lambda: None)
    result = await browser.fetch_tock_calendar(URL, "123", "http://user-session-fixed:password@proxy:8080")
    assert result == (HTML, bytes([218, 186, 29, 0]))
    engine.new_context.assert_awaited_once()
    assert engine.new_context.call_args.kwargs["proxy"]["username"] == "user-session-fixed"
    assert browser._solve_cloudflare_if_stuck.call_args.kwargs["context"] is context
    assert browser._solve_cloudflare_if_stuck.call_args.kwargs["page"] is page
    assert browser._solve_cloudflare_if_stuck.call_args.kwargs["proxy_url"] == "http://user-session-fixed:password@proxy:8080"
    assert page.evaluate.await_count == 2
    assert page.evaluate.call_args.args[1]["businessId"] == "123"
    context.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("loaded", ["", "456", None])
async def test_wrong_loaded_business_fails_before_calendar_request(browser_chain, loaded):
    browser, _, context, page = browser_chain
    page.evaluate.side_effect = [loaded]
    with pytest.raises(ValueError, match="business ID"):
        await browser.fetch_tock_calendar(URL, "123")
    assert page.evaluate.await_count == 1
    context.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsolved_challenge_does_not_request_calendar(browser_chain, monkeypatch):
    browser, _, context, page = browser_chain
    page.content.return_value = "<html>Just a moment...</html>"
    browser._wait_for_cloudflare_challenge = AsyncMock(return_value=page.content.return_value)
    browser._solve_cloudflare_if_stuck = AsyncMock(return_value=None)
    monkeypatch.setattr(module, "build_default_cloudflare_solver", lambda: None)
    with pytest.raises(RuntimeError, match="remains blocked"):
        await browser.fetch_tock_calendar(URL, "123")
    page.evaluate.assert_not_awaited()
    context.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [
    {"status": 403, "contentType": "application/octet-stream", "data": [1]},
    {"status": 200, "contentType": "text/html", "data": [1]},
    {"status": 200, "contentType": "application/octet-stream", "data": []},
    {"status": 200, "contentType": "application/octet-stream", "data": [256]},
    {"status": 200, "contentType": "application/octet-stream", "data": [True]},
    {"status": 200, "contentType": "application/octet-stream", "data": [0] * 9},
])
async def test_invalid_calendar_never_returns_fake_empty(browser_chain, monkeypatch, response):
    browser, _, context, page = browser_chain
    monkeypatch.setattr(module, "_TOCK_CALENDAR_MAX_BYTES", 8)
    page.evaluate.side_effect = ["123", response]
    with pytest.raises(RuntimeError, match="Tock calendar"):
        await browser.fetch_tock_calendar(URL, "123")
    context.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancelled_calendar_read_closes_context_and_releases_lock(browser_chain):
    browser, _, context, page = browser_chain
    entered = asyncio.Event()
    async def evaluate(script, *args):
        if not args:
            return "123"
        assert browser._browser_lock.locked()
        entered.set()
        await asyncio.Future()
    page.evaluate.side_effect = evaluate
    task = asyncio.create_task(browser.fetch_tock_calendar(URL, "123"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    context.close.assert_awaited_once()
    assert not browser._browser_lock.locked()


@pytest.mark.asyncio
async def test_identity_evaluation_has_timeout(browser_chain, monkeypatch):
    browser, _, context, page = browser_chain
    monkeypatch.setattr(module, "_TOCK_CALENDAR_TIMEOUT_MS", 1)
    async def hangs(*args):
        await asyncio.Future()
    page.evaluate.side_effect = hangs
    with pytest.raises(asyncio.TimeoutError):
        await browser.fetch_tock_calendar(URL, "123")
    context.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_origin_rejected_before_navigation(browser_chain):
    browser, engine, _, _ = browser_chain
    with pytest.raises(ValueError, match="HTTPS storefront"):
        await browser.fetch_tock_calendar("https://other.example/tock", "123")
    engine.new_context.assert_not_awaited()


# Execute the actual evaluate script against a mocked fetch/ReadableStream when
# Node is available; Python-only environments still run the lifecycle tests.
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node needed to execute browser JavaScript against mocks")
@pytest.mark.parametrize("case", ["success", "identity", "origin", "status", "mime", "size", "timeout"])
def test_browser_script_request_contract(case):
    harness = r'''
const vm = require('vm');
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
let request = null;
global.location = {origin: input.case === 'origin' ? 'https://wrong.example' : 'https://www.exploretock.com', pathname:'/batsu/experience/1/show'};
global.window = {$REDUX_STATE:{app:{activeAuth:{businessId:input.case==='identity'?456:123,businessGroupId:789},sessionToken:'test-session',csrfToken:{token:'test-csrf'}}},__BUILD_NUMBER__:42};
global.fetch = async (path, options) => {
    request = {path, method:options.method, headers:options.headers, body:Array.from(options.body), credentials:options.credentials, redirect:options.redirect};
    if (input.case === 'timeout') return new Promise((_, reject) => options.signal.addEventListener('abort', () => reject(new Error('aborted'))));
    let read = false;
    return {status:input.case==='status'?403:200,
        headers:{get:key=>key==='content-type'?(input.case==='mime'?'text/html':'application/octet-stream'):null},
        body:{getReader:()=>({read:async()=>read?{done:true}:(read=true,{done:false,value:new Uint8Array(input.case==='size'?[1,2,3,4,5]:[218,186,29,0])}),releaseLock:()=>{}})}};
};
(async()=>{try {const result=await vm.runInThisContext('('+input.script+')')({businessId:'123',origin:'https://www.exploretock.com',timeoutMs:5,maxBytes:4});process.stdout.write(JSON.stringify({result,request}));}
catch(e){process.stdout.write(JSON.stringify({error:e.message,request}));}})();
'''
    result = subprocess.run([NODE, "-e", harness], input=json.dumps({"case": case, "script": module._TOCK_CALENDAR_SCRIPT}), text=True, capture_output=True, check=True, timeout=5)
    output = json.loads(result.stdout)
    if case == "success":
        request = output["request"]
        assert request["path"] == "/api/consumer/calendar/full/v2"
        assert request["method"] == "POST"
        assert request["body"] == [218, 186, 29, 0]
        assert request["credentials"] == "same-origin"
        assert request["redirect"] == "error"
        headers = request["headers"]
        assert json.loads(headers["X-Tock-Scope"]) == {"businessId": "123", "businessGroupId": "789"}
        assert headers["X-Tock-Session"] == "test-session"
        assert headers["X-Tock-Csrf-Token"] == "test-csrf"
        assert headers["X-Tock-Build-Number"] == "42"
        assert headers["X-Tock-Stream-Format"] == "proto2"
        assert output["result"]["data"] == [218, 186, 29, 0]
    else:
        assert "error" in output
        if case in {"identity", "origin"}:
            assert output["request"] is None


def test_neutral_sticky_proxy_helper_preserves_tixr_compatibility(monkeypatch):
    from laughtrack.foundation.infrastructure.http import client
    monkeypatch.setattr(client.secrets, "token_hex", lambda size: "fixed")
    proxy = "http://user-test-session-old:secret@gate.decodo.com:10001"
    assert client.with_decodo_session(proxy) == client._with_tixr_decodo_session(proxy)
    assert "user-test-session-ltfixed" in client.with_decodo_session(proxy)
    assert client.with_decodo_session("http://user:secret@other.example:80") == "http://user:secret@other.example:80"
