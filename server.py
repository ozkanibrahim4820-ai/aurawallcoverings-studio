"""Local-only AuraWallCoverings workspace. No Etsy publishing or external writes."""
import argparse
from datetime import datetime, timezone
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sqlite3
import uuid
from urllib.parse import urlsplit

from domain import ValidationError, pricing, quality, text

ROOT = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, filename):
        self.filename = str(filename)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS products (
              id TEXT PRIMARY KEY, sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
              title TEXT NOT NULL, kind TEXT NOT NULL, notes TEXT NOT NULL,
              version INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS research (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL,
              observed_on TEXT NOT NULL, evidence TEXT NOT NULL, notes TEXT NOT NULL,
              created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audits (
              id INTEGER PRIMARY KEY, event TEXT NOT NULL, entity_id TEXT NOT NULL,
              before_json TEXT, after_json TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS evaluations (
              id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id),
              kind TEXT NOT NULL, input_json TEXT NOT NULL, result_json TEXT NOT NULL,
              created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pilot_checks (
              product_id TEXT NOT NULL REFERENCES products(id), step TEXT NOT NULL,
              status TEXT NOT NULL, evidence TEXT NOT NULL, updated_at TEXT NOT NULL,
              PRIMARY KEY(product_id, step));
            CREATE TABLE IF NOT EXISTS outputs (
              id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id),
              role TEXT NOT NULL, reference TEXT NOT NULL, payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL, UNIQUE(product_id, role, reference));
            """)

    def connect(self):
        db = sqlite3.connect(self.filename, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def audit(self, db, event, entity_id, before, after):
        db.execute("INSERT INTO audits(event,entity_id,before_json,after_json,created_at) VALUES(?,?,?,?,?)",
                   (event, entity_id, json.dumps(before) if before else None, json.dumps(after), now()))

    def snapshot(self):
        with self.connect() as db:
            result = {name: [dict(row) for row in db.execute(f"SELECT * FROM {name} ORDER BY {order} DESC LIMIT 500")]
                      for name, order in (("products", "updated_at"), ("research", "created_at"), ("audits", "id"), ("evaluations", "created_at"))}
        for item in result["evaluations"]:
            item["inputs"] = json.loads(item.pop("input_json"))
            item["result"] = json.loads(item.pop("result_json"))
        result["connections"] = {"etsy": "not_connected", "drive": "not_connected", "printmarkt": "not_connected", "runner": "not_configured"}
        with self.connect() as db:
            result["pilot_checks"] = [dict(row) for row in db.execute("SELECT * FROM pilot_checks ORDER BY updated_at DESC")]
            result["outputs"] = [dict(row) for row in db.execute("SELECT * FROM outputs ORDER BY created_at DESC LIMIT 500")]
        for item in result["outputs"]:
            item["payload"] = json.loads(item.pop("payload_json"))
        result["generated_at"] = now()
        result["shop"] = "AuraWallCoverings"
        result["limits"] = {"rows_per_section": 500}
        return result

    def product(self, data, product_id=None):
        title, sku = text(data, "title", 140), text(data, "sku", 64).upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,63}", sku):
            raise ValidationError("SKU 3–64 karakter; harf, rakam, - veya _ kullanın.")
        kind = text(data, "kind", 20)
        if kind not in ("seamless", "mural"):
            raise ValidationError("Tür seamless veya mural olmalı.")
        notes = text(data, "notes", 10000, required=False)
        with self.connect() as db:
            before = None
            if product_id:
                row = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
                if not row:
                    raise KeyError("Ürün bulunamadı.")
                before = dict(row)
                if type(data.get("version")) is not int or data["version"] != row["version"]:
                    raise FileExistsError("Kayıt başka bir işlemde değişti. Yenileyip tekrar deneyin.")
                cursor = db.execute("UPDATE products SET title=?,sku=?,kind=?,notes=?,version=version+1,updated_at=? WHERE id=? AND version=?",
                                   (title, sku, kind, notes, now(), product_id, data["version"]))
                if cursor.rowcount != 1:
                    raise FileExistsError("Kayıt değişti; yeniden okuyun.")
            else:
                product_id = str(uuid.uuid4())
                db.execute("INSERT INTO products VALUES(?,?,?,?,?,?,?,?)", (product_id, sku, title, kind, notes, 1, now(), now(),))
            after = dict(db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone())
            self.audit(db, "product.updated" if before else "product.planned", product_id, before, after)
            return after

    def add_research(self, data):
        title, source = text(data, "title", 200), text(data, "source", 1000)
        if urlsplit(source).scheme not in ("http", "https") or not urlsplit(source).hostname:
            raise ValidationError("Kaynak geçerli bir http(s) adresi olmalı.")
        if urlsplit(source).username or urlsplit(source).password:
            raise ValidationError("Kaynak adresine kimlik bilgisi eklemeyin.")
        observed = text(data, "observed_on", 10)
        from datetime import date
        try:
            observed_date = date.fromisoformat(observed)
        except ValueError:
            raise ValidationError("Gözlem tarihi YYYY-MM-DD olmalı.")
        if observed_date > date.today():
            raise ValidationError("Gözlem tarihi gelecekte olamaz.")
        evidence = text(data, "evidence", 20)
        if evidence not in ("measured", "estimate", "missing"):
            raise ValidationError("Kanıt türü geçersiz.")
        notes = text(data, "notes", 10000)
        with self.connect() as db:
            duplicate = db.execute("SELECT id FROM research WHERE source=? AND title=? AND observed_on=? AND notes=?", (source, title, observed, notes)).fetchone()
            if duplicate:
                raise FileExistsError("Aynı araştırma kaydı zaten mevcut.")
            item = dict(id=str(uuid.uuid4()), title=title, source=source, observed_on=observed, evidence=evidence, notes=notes, created_at=now())
            db.execute("INSERT INTO research VALUES(:id,:title,:source,:observed_on,:evidence,:notes,:created_at)", item)
            self.audit(db, "research.recorded", item["id"], None, item)
            return item

    def evaluate(self, data, kind):
        product_id = text(data, "product_id", 100)
        inputs = data.get("inputs")
        if not isinstance(inputs, dict):
            raise ValidationError("Hesap girdileri gerekli.")
        result = pricing(inputs) if kind == "pricing" else quality(inputs)
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM products WHERE id=?", (product_id,)).fetchone():
                raise KeyError("Ürün bulunamadı.")
            existing = db.execute("SELECT id,result_json FROM evaluations WHERE product_id=? AND kind=? AND input_json=?", (product_id, kind, json.dumps(inputs, sort_keys=True))).fetchone()
            if existing:
                return {"id": existing["id"], "result": json.loads(existing["result_json"]), "reused": True}
            identity = str(uuid.uuid4())
            db.execute("INSERT INTO evaluations VALUES(?,?,?,?,?,?)", (identity, product_id, kind, json.dumps(inputs, sort_keys=True), json.dumps(result), now()))
            self.audit(db, f"{kind}.evaluated", product_id, None, {"evaluation_id": identity, "result": result})
            return {"id": identity, "result": result, "reused": False}

    def pilot_check(self, data):
        product_id = text(data, "product_id", 100)
        step = text(data, "step", 40)
        if step not in ("duplicates", "research", "creative", "print", "mockups", "pricing", "seo", "etsy", "drive"):
            raise ValidationError("Pilot kontrol adımı geçersiz.")
        status = text(data, "status", 20)
        if status not in ("not_started", "in_progress", "blocked", "reviewed"):
            raise ValidationError("Pilot kontrol durumu geçersiz.")
        evidence = text(data, "evidence", 10000, required=status != "not_started")
        if step in ("etsy", "drive") and status == "reviewed":
            raise ValidationError("Harici bağlantı doğrulanmadan Etsy/Drive adımı doğrulanmış olarak işaretlenemez.")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM products WHERE id=?", (product_id,)).fetchone():
                raise KeyError("Ürün bulunamadı.")
            row = db.execute("SELECT * FROM pilot_checks WHERE product_id=? AND step=?", (product_id, step)).fetchone()
            before = dict(row) if row else None
            # Compare the last known timestamp to prevent silent concurrent overwrites.
            if before and data.get("expected_updated_at") != before["updated_at"]:
                raise FileExistsError("Kontrol başka bir işlemde değişti.")
            if not before and data.get("expected_updated_at"):
                raise FileExistsError("Kontrol kaydı değişti.")
            item = dict(product_id=product_id, step=step, status=status, evidence=evidence, updated_at=now())
            db.execute("INSERT INTO pilot_checks VALUES(:product_id,:step,:status,:evidence,:updated_at) ON CONFLICT(product_id,step) DO UPDATE SET status=excluded.status,evidence=excluded.evidence,updated_at=excluded.updated_at", item)
            self.audit(db, "pilot.manual_review", product_id, before, item)
            return item

    def add_output(self, data):
        product_id = text(data, "product_id", 100)
        role = text(data, "role", 20)
        if role not in ("design", "mockup", "seo"):
            raise ValidationError("Çıktı türü geçersiz.")
        reference = text(data, "reference", 2000)
        parsed = urlsplit(reference)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValidationError("Kimlik bilgisi içermeyen geçerli bir kaynak/çıktı URL'si gerekli.")
        notes = text(data, "notes", 10000, required=False)
        payload = {"provider": "Printmarkt", "evidence": "manual_import", "externally_verified": False, "notes": notes}
        if role == "seo":
            payload["title"] = text(data, "title", 140)
            payload["description"] = text(data, "description", 30000)
            tags = data.get("tags")
            if not isinstance(tags, list) or not 1 <= len(tags) <= 13:
                raise ValidationError("SEO kaydı 1–13 etiket içermeli.")
            normalized = []
            for tag in tags:
                value = text({"tag": tag}, "tag", 20)
                if value.casefold() in [t.casefold() for t in normalized]:
                    raise ValidationError("Yinelenen SEO etiketi var.")
                normalized.append(value)
            payload["tags"] = normalized
        if role == "mockup":
            payload["alt_text"] = text(data, "alt_text", 500)
            payload["scale_color_review"] = "not_verified"
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM products WHERE id=?", (product_id,)).fetchone():
                raise KeyError("Ürün bulunamadı.")
            item = dict(id=str(uuid.uuid4()), product_id=product_id, role=role, reference=reference, payload_json=json.dumps(payload), created_at=now())
            db.execute("INSERT INTO outputs VALUES(:id,:product_id,:role,:reference,:payload_json,:created_at)", item)
            self.audit(db, "printmarkt.output_recorded", product_id, None, {"output_id": item["id"], "role": role, "evidence": "manual_import"})
            return {"id": item["id"], "payload": payload, "reference": reference}


def handler_factory(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Avoid logging request bodies, query strings or credentials.
            pass

        def send(self, status, value, content_type="application/json; charset=utf-8"):
            payload = json.dumps(value, ensure_ascii=False).encode() if content_type.startswith("application/json") else value
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
            self.end_headers()
            self.wfile.write(payload)

        def allowed(self):
            expected_hosts = {f"localhost:{self.server.server_port}", f"127.0.0.1:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in expected_hosts or (origin and origin not in {f"http://{h}" for h in expected_hosts}):
                self.send(403, {"error": "Yalnızca yerel, aynı kaynaklı erişim destekleniyor."})
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            if path == "/api/state":
                return self.send(200, store.snapshot())
            if path == "/api/health":
                with store.connect() as db:
                    db.execute("SELECT 1").fetchone()
                return self.send(200, {"local_app": "ok", "database": "ok", "external_connections": "not_verified"})
            files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
            if path not in files:
                return self.send(404, {"error": "Bulunamadı."})
            name, mime = files[path]
            self.send(200, (ROOT / "static" / name).read_bytes(), mime)

        def do_POST(self):
            self.mutate()

        def do_PATCH(self):
            self.mutate()

        def mutate(self):
            if not self.allowed():
                return
            try:
                if self.headers.get_content_type() != "application/json":
                    raise ValidationError("JSON içerik gerekli.")
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 100_000:
                    raise ValidationError("İstek boyutu geçersiz.")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValidationError("JSON nesnesi gerekli.")
                path = urlsplit(self.path).path
                if self.command == "POST" and path == "/api/products":
                    result = store.product(data)
                elif self.command == "PATCH" and re.fullmatch(r"/api/products/[a-f0-9-]{36}", path):
                    result = store.product(data, path.split("/")[-1])
                elif self.command == "POST" and path == "/api/research":
                    result = store.add_research(data)
                elif self.command == "POST" and path == "/api/pilot-checks":
                    result = store.pilot_check(data)
                elif self.command == "POST" and path == "/api/outputs":
                    result = store.add_output(data)
                elif self.command == "POST" and path in ("/api/pricing", "/api/quality"):
                    result = store.evaluate(data, path.split("/")[-1])
                else:
                    return self.send(404, {"error": "İşlem desteklenmiyor. Etsy/Drive yazma işlemi bulunmuyor."})
                self.send(200, result)
            except ValidationError as error:
                self.send(400, {"error": str(error)})
            except (ValueError, json.JSONDecodeError):
                self.send(400, {"error": "Girdileri kontrol edin; zorunlu alanlar, tarih, sayılar ve matrah seçimleri geçerli olmalı."})
            except (sqlite3.IntegrityError, FileExistsError):
                self.send(409, {"error": "SKU veya kayıt zaten mevcut ya da sürümü değişmiş. Yenileyerek kontrol edin."})
            except KeyError:
                self.send(404, {"error": "Ürün bulunamadı."})
            except Exception:
                self.send(500, {"error": "İşlem tamamlanamadı; kayıtları kontrol etmeden tekrar göndermeyin."})
    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", default=str(ROOT / "data" / "studio.sqlite3"))
    parser.add_argument("--open-browser", action="store_true", help="Yerel bilgisayarda varsayılan tarayıcıyı aç")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_factory(Store(args.db)))
    print(f"AuraWallCoverings local server listening on port {args.port}", flush=True)
    if args.open_browser:
        import threading
        import webbrowser
        threading.Timer(0.5, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    server.serve_forever()
