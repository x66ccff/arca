from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "arca"


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
        self.assertNotIn("<script src=", generated)
        self.assertNotIn("cdn.jsdelivr.net", generated)

        refused = self.cli("visualize", str(output), check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.cli("visualize", str(output), "--force")
        self.cli("visualize")
        self.assertTrue((self.library / "_index" / "paper-graph.html").exists())


if __name__ == "__main__":
    unittest.main()
