"""Optional real-browser smoke check, isolated from all user data.

Requires Playwright Python and an existing Chromium executable. Neither is a
runtime dependency of the app. Run from the repository root.
"""
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import threading
import zlib
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Store, handler_factory


def fixture_png():
    def chunk(name, content):
        return struct.pack(">I", len(content)) + name + content + struct.pack(">I", zlib.crc32(name + content) & 0xFFFFFFFF)
    width = height = 600
    colors = ((b"\x52\x78\x5e", b"\xc8\x8c\x5a"), (b"\x8c\xaa\x78", b"\xe1\xe6\xd2"))
    pixels = b"".join(b"\x00" + colors[int(y >= 300)][0] * 300 + colors[int(y >= 300)][1] * 300 for y in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def main():
    from playwright.sync_api import sync_playwright
    chromium = shutil.which("chromium") or shutil.which("google-chrome")
    if not chromium:
        raise SystemExit("Existing Chromium required; no browser is installed by this script.")
    with tempfile.TemporaryDirectory() as temp:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(Store(Path(temp) / "test.sqlite3")))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=chromium, headless=True, args=["--no-sandbox"])
                page = browser.new_page(viewport={"width":1440, "height":1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.locator("nav [data-view=products]").click()
                page.locator("#add-product").click()
                page.locator('#product-form [name="title"]').fill("Browser smoke fixture — TEST ONLY")
                page.locator('#product-form [name="sku"]').fill("BROWSER-001")
                page.locator('#product-form button[type="submit"]').click()
                page.locator("#product-list h3").wait_for()
                page.locator("nav [data-view=files]").click()
                page.locator('#asset-form [name="product_id"]').select_option(index=1)
                page.locator('#asset-form [name="file"]').set_input_files({"name":"browser-fixture.png", "mimeType":"image/png", "buffer":fixture_png()})
                page.locator('#asset-form button[type="submit"]').click()
                page.locator("[data-repeat]").wait_for()
                page.locator("[data-repeat]").click()
                page.locator("#repeat-review").wait_for(state="visible")
                page.wait_for_function("document.querySelector('#repeat-canvas').width === 900")
                # Nine tiles must each preserve all four colored quadrants. This
                # fails for one stretched image, omitted tiles or blank canvas.
                samples = page.locator("#repeat-canvas").evaluate("c => {const ctx=c.getContext('2d'),samples=[];for(let y=0;y<3;y++)for(let x=0;x<3;x++)for(const [dx,dy] of [[75,75],[225,75],[75,225],[225,225]])samples.push(Array.from(ctx.getImageData(x*300+dx,y*300+dy,1,1).data));return samples;}")
                expected = [[82,120,94,255], [200,140,90,255], [140,170,120,255], [225,230,210,255]] * 9
                assert samples == expected, samples
                # Chromium encodes a real JPEG, then the server metadata reader
                # inspects it; this verifies SOF parsing on a decoded/encoded image.
                jpeg = page.locator("#repeat-canvas").evaluate("c => c.toDataURL('image/jpeg').split(',')[1]")
                import base64
                from images import image_metadata
                assert image_metadata(base64.b64decode(jpeg))["width_px"] == 900
                page.screenshot(path="/tmp/aurawall-repeat-browser-check.png", full_page=True)
                page.locator("nav [data-view=quality]").click()
                page.locator('#quality-form [name="product_id"]').select_option(index=1)
                page.locator("#quality-asset").select_option(index=1)
                assert page.locator('#quality-form [name="width_px"]').input_value() == "600"
                assert page.locator('#quality-form [name="width_px"]').get_attribute("readonly") is not None
                page.locator('#quality-form [name="width_cm"]').fill("2.54")
                page.locator('#quality-form [name="height_cm"]').fill("2.54")
                page.locator('#quality-form button[type="submit"]').click()
                page.locator("#quality-result").wait_for(state="visible")
                assert "600" in page.locator("#quality-result").inner_text()
                assert "Baskıya hazır onayı verilmedi" in page.locator("#quality-result").inner_text()
                assert not errors, errors
                browser.close()
                print(json.dumps({"browser":"Chromium", "product_create":"passed", "file_upload":"passed", "repeat_canvas_pixels":"passed", "file_dimensions_to_quality":"passed", "page_errors":errors, "user_data":"untouched; temporary database"}, ensure_ascii=False))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    main()
