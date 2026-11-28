#!/usr/bin/env python3
"""Run axe-core WCAG 2.2 AA and best-practice audits on all seven packaged routes."""
from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "dist"
AXE_SCRIPT = ROOT / "node_modules" / "axe-core" / "axe.min.js"
ROUTES = (
    "/",
    "/booking.html",
    "/library.html",
    "/policies.html",
    "/admin.html",
    "/client-gallery.html",
    "/404.html",
)
WCAG_TAGS = (
    "wcag2a",
    "wcag2aa",
    "wcag21a",
    "wcag21aa",
    "wcag22aa",
    "best-practice",
)
FAIL_IMPACTS = {"critical", "serious"}


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def do_GET(self):
        # Serve axe-core from the test-only node_modules path on the same origin.
        # This respects pages that enforce script-src 'self' through CSP meta tags.
        if self.path.split("?", 1)[0] == "/__axe__/axe.min.js":
            payload = AXE_SCRIPT.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


def main() -> None:
    assert SITE.is_dir(), f"Packaged site directory is missing: {SITE}"
    assert AXE_SCRIPT.is_file(), (
        f"axe-core is not installed at {AXE_SCRIPT}; install the pinned npm package first"
    )
    for route in ROUTES:
        target = SITE / route.lstrip("/") if route != "/" else SITE / "index.html"
        assert target.is_file() and target.stat().st_size > 0, f"Missing packaged route: {route}"

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    all_violations: list[dict] = []
    failures: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                viewport={"width": 1365, "height": 900},
                reduced_motion="reduce",
            )
            # Third-party challenge/model frames are outside the local static-page audit.
            context.route("https://**", lambda route: route.abort())

            for route in ROUTES:
                page = context.new_page()
                response = page.goto(base_url + route, wait_until="domcontentloaded")
                assert response is not None and response.status == 200, (
                    f"{route}: packaged route did not load (response={response})"
                )
                page.add_script_tag(url=base_url + "/__axe__/axe.min.js")
                results = page.evaluate(
                    """async (tags) => {
                        const result = await axe.run(document, {
                            runOnly: { type: "tag", values: tags },
                            resultTypes: ["violations", "incomplete"]
                        });
                        return {
                            violations: result.violations.map(item => ({
                                id: item.id,
                                impact: item.impact,
                                help: item.help,
                                helpUrl: item.helpUrl,
                                nodes: item.nodes.map(node => ({
                                    target: node.target,
                                    failureSummary: node.failureSummary
                                }))
                            })),
                            incomplete: result.incomplete.map(item => ({
                                id: item.id,
                                impact: item.impact,
                                help: item.help,
                                nodes: item.nodes.length
                            }))
                        };
                    }""",
                    list(WCAG_TAGS),
                )

                route_failures = [
                    item for item in results["violations"]
                    if item.get("impact") in FAIL_IMPACTS
                ]
                all_violations.extend(
                    {"route": route, **item} for item in results["violations"]
                )
                failures.extend(
                    f"{route}: {item['id']} ({item.get('impact')})"
                    for item in route_failures
                )

                moderate = sum(
                    item.get("impact") == "moderate"
                    for item in results["violations"]
                )
                minor = sum(
                    item.get("impact") == "minor"
                    for item in results["violations"]
                )
                print(
                    f"{route}: {len(results['violations'])} violation rule(s); "
                    f"{len(route_failures)} critical/serious, "
                    f"{moderate} moderate, {minor} minor; "
                    f"{len(results['incomplete'])} items need manual review."
                )
                page.close()

            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    report_path = ROOT / "axe-accessibility-report.json"
    report_path.write_text(
        json.dumps(
            {
                "routes": list(ROUTES),
                "tags": list(WCAG_TAGS),
                "fail_impacts": sorted(FAIL_IMPACTS),
                "violations": all_violations,
                "failures": failures,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"axe-core report written to {report_path}")
    if failures:
        raise AssertionError(
            "Serious/critical accessibility violations found: " + "; ".join(failures)
        )
    print("PASS axe-core: no critical or serious WCAG 2.2 AA/best-practice violations.")


if __name__ == "__main__":
    main()
