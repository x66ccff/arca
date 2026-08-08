from __future__ import annotations

import json
import importlib.machinery
import importlib.util
import io
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "arca"


def load_cli_module():
    loader = importlib.machinery.SourceFileLoader("arca_cli", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


ARCA = load_cli_module()


class ReviewTerminal:
    def __init__(self, response: str) -> None:
        self.response = response
        self.output = io.StringIO()

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def write(self, value: str) -> int:
        return self.output.write(value)

    def flush(self) -> None:
        pass

    def readline(self) -> str:
        return self.response

    def getvalue(self) -> str:
        return self.output.getvalue()


def record(paper_id: str, title: str) -> dict:
    return {
        "schema_version": 1,
        "id": paper_id,
        "type": "preprint",
        "title": title,
        "authors": [{"name": "Ada Agent"}],
        "abstract": f"Abstract for {title}",
        "published": "2024-01-01",
        "updated": "2024-01-02",
        "source": {
            "provider": "arxiv",
            "id": paper_id,
            "version": 1,
            "url": f"https://arxiv.org/abs/{paper_id}",
            "pdf_url": f"https://arxiv.org/pdf/{paper_id}.pdf",
        },
        "status": "inbox",
        "tags": [],
        "collections": [],
        "files": {"pdf": None},
        "provenance": [],
        "aliases": [],
        "added_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "custom": {"preserve_me": True},
        "extension_field": {"must_survive": True},
    }


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.library = self.base / "library"
        self.cli("init", str(self.library), library=False)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def cli(self, *args: str, library: bool = True, check: bool = True) -> subprocess.CompletedProcess[str]:
        command = [str(CLI)]
        if library:
            command += ["--library", str(self.library)]
        command += list(args)
        return subprocess.run(command, text=True, capture_output=True, check=check)

    def fixture(self, paper_id: str, title: str) -> tuple[Path, Path]:
        metadata = self.base / f"{paper_id}.json"
        metadata.write_text(json.dumps(record(paper_id, title)), encoding="utf-8")
        pdf = self.base / f"{paper_id}.pdf"
        pdf.write_bytes(b"%PDF-1.7\n" + b"0" * 11000)
        return metadata, pdf

    def ingest(self, paper_id: str, title: str) -> None:
        metadata, pdf = self.fixture(paper_id, title)
        self.cli("ingest", str(metadata), "--pdf", str(pdf), "--json")

    def test_crud_notes_annotations_graph_and_recovery(self) -> None:
        self.ingest("2401.00001", "First Paper")
        self.ingest("2401.00002", "Second Paper")

        self.cli("update", "2401.00001", "--status", "key", "--add-tag", "reasoning", "--json")
        self.cli("note", "2401.00001", "Important connection to the second paper.")
        annotation = json.loads(self.cli(
            "annotate", "2401.00001", "--page", "3", "--quote", "a useful result",
            "--comment", "Recheck this proof", "--tag", "proof", "--json",
        ).stdout)[0]
        self.assertEqual(annotation["page"], 3)

        edge = json.loads(self.cli(
            "link", "2401.00002", "extends", "2401.00001",
            "--note", "Builds on the first result", "--json",
        ).stdout)[0]
        neighborhood = json.loads(self.cli("neighbors", "2401.00001", "--json").stdout)
        self.assertEqual(len(neighborhood["nodes"]), 2)
        self.assertEqual(len(neighborhood["edges"]), 1)
        self.assertIn("digraph papers", self.cli("graph", "--format", "dot").stdout)

        search = json.loads(self.cli("search", "Important connection", "--json").stdout)
        self.assertEqual([item["id"] for item in search], ["2401.00001"])
        stored = json.loads(self.cli("get", "2401.00001", "--json").stdout)[0]
        self.assertTrue(stored["custom"]["preserve_me"])
        self.assertTrue(stored["extension_field"]["must_survive"])
        self.assertEqual(stored["status"], "key")

        self.cli("unlink", edge["id"])
        self.cli("remove", "2401.00002", "--yes")
        self.assertEqual(len(json.loads(self.cli("list", "--json").stdout)), 1)
        self.cli("restore", "2401.00002")
        self.assertEqual(len(json.loads(self.cli("list", "--json").stdout)), 2)

        report = json.loads(self.cli("doctor", "--full", "--json").stdout)[0]
        self.assertTrue(report["ok"])
        self.assertEqual(report["papers"], 2)

    def test_rejects_tiny_pdf_transactionally(self) -> None:
        metadata, pdf = self.fixture("2401.00003", "Tiny PDF")
        pdf.write_bytes(b"%PDF-1.7\nsmall")
        result = self.cli("ingest", str(metadata), "--pdf", str(pdf), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.library / "papers" / "2401.00003").exists())

    def test_visualize_generates_offline_html(self) -> None:
        self.ingest("2401.00011", "Older Paper")
        self.ingest("2401.00012", "Newer Paper")
        self.cli("link", "2401.00012", "extends", "2401.00011")

        output = self.base / "paper-graph.html"
        result = self.cli("visualize", str(output), "--title", "Test Paper Graph")
        self.assertEqual(Path(result.stdout.strip()), output.resolve())
        generated = output.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", generated)
        self.assertIn("Test Paper Graph", generated)
        self.assertIn('"id":"2401.00011"', generated)
        self.assertIn('"degree":1', generated)
        self.assertIn("const yearOpacity", generated)
        self.assertIn('class="sync-panel"', generated)
        self.assertIn('class="sync-button"', generated)
        self.assertIn("离线页面，运行 arca serve 启用按钮", generated)
        self.assertIn("connect-src 'self'", generated)
        self.assertIn('"sync":{"state":"never"', generated)
        self.assertNotIn("<script src=", generated)
        self.assertNotIn("cdn.jsdelivr.net", generated)

        refused = self.cli("visualize", str(output), check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.cli("visualize", str(output), "--force")
        self.cli("visualize")
        self.assertTrue((self.library / "_index" / "paper-graph.html").exists())

    def test_loopback_graph_service_status_and_sync(self) -> None:
        self.ingest("2401.00031", "Service Paper")
        self.cli("visualize")
        server = ARCA.build_graph_server(self.library, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"

        def fake_sync(root: Path) -> dict:
            payload = {
                "schema_version": 1,
                "generated_at": "2024-01-03T00:00:00Z",
                "provider": "semantic-scholar",
                "provider_url": "https://api.semanticscholar.org/graph/v1",
                "works": [{
                    "local_id": "2401.00031",
                    "query": "ARXIV:2401.00031",
                    "paper_id": "service-paper-id",
                    "external_ids": {"ArXiv": "2401.00031"},
                    "references": [],
                }],
            }
            ARCA.write_json(root / "_index" / "citation-cache.json", payload)
            return {"papers": 1, "resolved": 1, "references": 0}

        try:
            with urllib.request.urlopen(f"{base_url}/api/sync-status", timeout=5) as handle:
                status_payload = json.load(handle)
            self.assertTrue(status_payload["ok"])
            self.assertTrue(status_payload["sync_token"])

            rebound = urllib.request.Request(
                f"{base_url}/api/sync-status", headers={"Host": "research.example"}
            )
            with self.assertRaises(urllib.error.HTTPError) as blocked_host:
                urllib.request.urlopen(rebound, timeout=5)
            self.assertEqual(blocked_host.exception.code, 403)

            unauthorized = urllib.request.Request(
                f"{base_url}/api/citation-sync", data=b"", method="POST"
            )
            with self.assertRaises(urllib.error.HTTPError) as rejected:
                urllib.request.urlopen(unauthorized, timeout=5)
            self.assertEqual(rejected.exception.code, 403)

            authorized = urllib.request.Request(
                f"{base_url}/api/citation-sync",
                data=b"",
                method="POST",
                headers={"X-Arca-Sync-Token": status_payload["sync_token"]},
            )
            with mock.patch.object(ARCA, "sync_semantic_scholar_citations", side_effect=fake_sync):
                with urllib.request.urlopen(authorized, timeout=5) as handle:
                    synced = json.load(handle)
            self.assertTrue(synced["ok"])
            self.assertEqual(synced["status"]["resolved_papers"], 1)
            self.assertIn(
                '"resolved_papers":1',
                (self.library / "_index" / "paper-graph.html").read_text(encoding="utf-8"),
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_unresolved_provider_record_does_not_mark_sync_failed(self) -> None:
        self.ingest("2401.00041", "Resolved Paper")
        self.ingest("2401.00042", "Provider Missing Paper")
        ARCA.write_json(self.library / "_index" / "citation-cache.json", {
            "schema_version": 1,
            "generated_at": ARCA.now(),
            "provider": "semantic-scholar",
            "works": [
                {
                    "local_id": "2401.00041",
                    "paper_id": "resolved-id",
                    "external_ids": {"ArXiv": "2401.00041"},
                    "references": [],
                },
                {
                    "local_id": "2401.00042",
                    "paper_id": None,
                    "external_ids": {},
                    "references": [],
                },
            ],
        })
        status = ARCA.citation_sync_status(self.library)
        self.assertEqual(status["state"], "current")
        self.assertEqual(status["label"], "已同步")
        self.assertEqual(status["missing_papers"], 0)
        self.assertEqual(status["unresolved_papers"], 1)
        self.assertEqual(status["unresolved_ids"], ["2401.00042"])

    def test_star_remark_and_visual_glow(self) -> None:
        self.ingest("2401.00021", "Starred Paper")
        starred = json.loads(
            self.cli("star", "2401.00021", "--json").stdout
        )[0]
        self.assertTrue(starred["starred"])
        self.assertEqual(
            [item["id"] for item in json.loads(self.cli("list", "--starred", "--json").stdout)],
            ["2401.00021"],
        )

        review = mock.Mock()
        with mock.patch.object(ARCA, "require_human_remark_review", review):
            with redirect_stdout(io.StringIO()):
                result = ARCA.main([
                    "--library", str(self.library), "remark", "2401.00021",
                    "--text", "一句准确注记", "--json",
                ])
        self.assertEqual(result, 0)
        review.assert_called_once()

        stored = json.loads(self.cli("get", "2401.00021", "--json").stdout)[0]
        self.assertTrue(stored["starred"])
        self.assertEqual(stored["remark"], "一句准确注记")
        self.assertTrue(stored["remark_reviewed_at"])

        output = self.base / "starred-graph.html"
        self.cli("visualize", str(output))
        generated = output.read_text(encoding="utf-8")
        self.assertIn('"starred":true', generated)
        self.assertIn('"remark":"一句准确注记"', generated)
        self.assertIn(".node.starred", generated)
        self.assertIn("drop-shadow", generated)

        unstarred = json.loads(
            self.cli("unstar", "2401.00021", "--json").stdout
        )[0]
        self.assertFalse(unstarred["starred"])

    def test_remark_validation_and_human_confirmation(self) -> None:
        self.assertEqual(ARCA.normalized_remark("  精简注记  "), "精简注记")
        with self.assertRaises(ARCA.ArcaError):
            ARCA.normalized_remark("x" * 31)
        with self.assertRaises(ARCA.ArcaError):
            ARCA.normalized_remark("两行\n注记")

        proposal = {"id": "x", "title": "Review Me"}
        approved_terminal = ReviewTerminal("确认\n")
        with mock.patch("builtins.open", return_value=approved_terminal):
            ARCA.require_human_remark_review(proposal, "准确注记")
        self.assertIn("长度：4/30", approved_terminal.getvalue())

        rejected_terminal = ReviewTerminal("不确认\n")
        with mock.patch("builtins.open", return_value=rejected_terminal):
            with self.assertRaises(ARCA.ArcaError):
                ARCA.require_human_remark_review(proposal, "准确注记")


if __name__ == "__main__":
    unittest.main()
