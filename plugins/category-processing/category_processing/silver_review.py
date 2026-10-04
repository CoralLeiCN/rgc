"""Local human review and durable corrections for verified Silver snapshots."""

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .archive import digest, inside, pointer_value, read_json
from .silver_contracts import validate_result
from .silver_snapshot import no_links, read_rows, verified_snapshot
from .source_index import SourceIndex, encoded


class ReviewSession:
    def __init__(self, silver_root, state_db, archive_root=None):
        self.root, self.manifest = verified_snapshot(silver_root)
        self.state_db = no_links(state_db)
        if inside(self.state_db, self.root):
            raise ValueError("Corrections must be stored outside the immutable snapshot.")
        self.profile = read_json(self.root / "profile.json")
        self.mappings = read_json(self.root / "source-mappings.json")
        self.facts = [item for item in read_rows(self.root / "facts.jsonl") if item["is_current"]]
        self.assertions = read_rows(self.root / "assertions.jsonl")
        self.archive = no_links(archive_root) if archive_root else None
        if self.archive and inside(self.state_db, self.archive):
            raise ValueError("The correction store must be outside Bronze.")
        with SourceIndex(self.state_db) as index:
            index.restore(read_json(self.root / "source-index.json"))
            index.restore_history(read_rows(self.root / "corrections.jsonl"))

    def inspect(self, subject):
        with SourceIndex(self.state_db) as index:
            history = index.history(subject)
        facts = [item for item in self.facts if item["subject_id"] == subject]
        evidence = [item for item in self.assertions if item["subject_id"] == subject and item["is_current"]]
        return {"facts": facts, "assertions": evidence, "history": history}

    def save(self, request):
        selected = [item for item in self.facts if item["subject_id"] == request["subject_id"]
                    and item["field"] == request["field"] and item["context"] == request["context"]]
        if len(selected) != 1:
            raise ValueError("Select exactly one current subject, field and context.")
        fact = selected[0]
        result = validate_result(fact["field"], request["result"], self.profile, self.mappings)
        sources = request.get("source", fact["source"])
        known = {encoded(ref) for item in self.facts if item["subject_id"] == fact["subject_id"] for ref in item["source"]}
        if not isinstance(sources, list) or any(encoded(ref) not in known for ref in sources):
            raise ValueError("Select supporting references from this subject's current evidence.")
        if result is not None and not sources:
            raise ValueError("A value or explicit state requires supporting source evidence.")
        # Saving against changed Bronze requires a rebuild and inspection of the new evidence.
        if self.archive:
            for ref in fact["source"]:
                path = no_links(self.archive / ref["bronze_path"])
                if not inside(path, self.archive):
                    raise ValueError("Evidence escapes the Bronze archive.")
                capture = read_json(path)
                if digest(capture) != ref["capture_sha256"]:
                    raise ValueError("Bronze evidence changed; rebuild before reviewing.")
                pointer_value(capture, ref["pointer"])
        decision = {key: fact[key] for key in ("subject_id", "field", "context", "definition_hash", "evidence_hash", "source")}
        decision["source"] = sources
        decision["additional_source"] = [ref for ref in sources if ref not in fact["source"]]
        with SourceIndex(self.state_db) as index:
            history = [item for item in index.history(fact["subject_id"])
                       if item["field"] == fact["field"] and item["context"] == fact["context"]]
            prior = history[-1]["result"] if history else fact["result"]
            decision.update(result=result, prior_result=prior, automatic_result=fact["prior_result"],
                            reviewer=request["reviewer"], reason=request["reason"],
                            silver_dataset_version=self.manifest["dataset_version"])
            return index.save(decision, request.get("expected_previous"))


PAGE = """<!doctype html><meta charset="utf-8"><title>Silver evidence review</title>
<style>body{font:16px system-ui;max-width:1100px;margin:36px auto;padding:0 20px}select,input,textarea,button{font:inherit;margin:5px;padding:7px}textarea{width:90%;height:90px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f4f6;padding:12px}label{display:block}</style>
<h1>Silver evidence review</h1><p>Inspect one source subject and semantic context. Saving creates a durable human correction. Rebuild Silver to apply it to generated data and reports.</p>
<label>Source subject <select id="subjects"></select></label><label>Field and context <select id="fields"></select></label>
<h2>Evidence and effective result</h2><pre id="evidence"></pre><h2>Correction history</h2><pre id="history"></pre>
<label>Accepted value or state (JSON; null means missing)<textarea id="result"></textarea></label>
<label>Supporting source references (copy references from this subject's evidence when filling a missing field)<textarea id="sources"></textarea></label>
<label>Your name <input id="reviewer"></label><label>Reason <input id="reason" size="70"></label>
<button id="save">Save human decision</button><p id="status" role="status"></p>
<script>
const token=TOKEN; let packet={}, selected=null, previous=null;
const el=id=>document.getElementById(id);
async function load(){packet=await(await fetch('/api/subject?id='+encodeURIComponent(el('subjects').value))).json();el('fields').replaceChildren();packet.facts.forEach((f,i)=>el('fields').add(new Option(f.field+' '+JSON.stringify(f.context),i)));show();}
function show(){selected=packet.facts[Number(el('fields').value)];if(!selected)return;const hist=packet.history.filter(h=>h.field===selected.field&&JSON.stringify(h.context)===JSON.stringify(selected.context));previous=hist.length?hist.at(-1):null;el('evidence').textContent=JSON.stringify({fact:selected,candidates:packet.assertions.filter(a=>a.field===selected.field&&JSON.stringify(a.context)===JSON.stringify(selected.context))},null,2);el('history').textContent=JSON.stringify(hist,null,2);el('result').value=JSON.stringify(previous?previous.result:selected.result,null,2);el('sources').value=JSON.stringify(previous?previous.source:selected.source,null,2);}
el('subjects').onchange=load;el('fields').onchange=show;
el('save').onclick=async()=>{try{const r=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,subject_id:selected.subject_id,field:selected.field,context:selected.context,result:JSON.parse(el('result').value),source:JSON.parse(el('sources').value),reviewer:el('reviewer').value,reason:el('reason').value,expected_previous:previous?previous.correction_id:null})});const data=await r.json();if(!r.ok)throw Error(data.error);el('status').textContent='Saved '+data.correction_id+'. Rebuild Silver to apply this correction.';const keep=el('fields').value;await load();el('fields').value=keep;show();}catch(e){el('status').textContent=e.message;}};
fetch('/api/subjects').then(r=>r.json()).then(rows=>{rows.forEach(r=>el('subjects').add(new Option(r.subject_id+' — '+r.source_key,r.subject_id)));load();});
</script>"""


def serve(silver_root, state_db, archive_root=None, port=8765):
    session = ReviewSession(silver_root, state_db, archive_root)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def response(self, status, value, html=False):
            data = value.encode() if html else encoded(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def local_host(self):
            return self.headers.get("Host") in ("127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port))

        def do_GET(self):
            if not self.local_host():
                return self.response(403, {"error": "Use the local review address."})
            path = urlsplit(self.path)
            if path.path == "/":
                return self.response(200, PAGE.replace("TOKEN", json.dumps(token)), html=True)
            if path.path == "/api/subjects":
                return self.response(200, read_rows(session.root / "subjects.jsonl"))
            if path.path == "/api/subject":
                return self.response(200, session.inspect(parse_qs(path.query).get("id", [""])[0]))
            return self.response(404, {"error": "Not found"})

        def do_POST(self):
            if not self.local_host() or self.path != "/api/save":
                return self.response(403, {"error": "Use the local review interface."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    raise ValueError("Invalid request size.")
                request = json.loads(self.rfile.read(length))
                if not secrets.compare_digest(str(request.pop("token", "")), token):
                    return self.response(403, {"error": "Reload the local review page."})
                return self.response(200, session.save(request))
            except (ValueError, TypeError, KeyError, OSError) as error:
                return self.response(400, {"error": str(error)})

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print("Silver review: http://127.0.0.1:" + str(server.server_port), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
