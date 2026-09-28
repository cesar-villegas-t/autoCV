import copy
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from types import SimpleNamespace as Namespace
from autocv.domain import text, models, files
from autocv.infrastructure.latex import renderer, compiler
from autocv.infrastructure.llm import gemini
from autocv.prompts import resume
cv = Namespace(**{name: getattr(module, name) for module, names in [
    (text, ['plain', 'tex']), (models, ['parse_resume']),
    (files, ['normalized_pdf_name']), (renderer, ['render']),
    (compiler, ['compile_and_copy_pdf', 'shutil', 'subprocess']),
    (gemini, ['call_gemini']), (resume, ['SYSTEM', 'prompt'])
] for name in names}, MODEL='gemini-3.5-flash-lite')


from tests.fixtures.resume import sample_resume


def escape_values(value):
    if isinstance(value, dict):
        return {key: escape_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [escape_values(item) for item in value]
    return cv.tex(value)


class ResumeTests(unittest.TestCase):
    def test_complete_history_and_long_fields_survive(self):
        source = sample_resume()
        source["experience"][2]["bullets"].append(
            "Engineered " + "documented pipeline components, " * 10 + "reducing runtime by 42%."
        )
        parsed = cv.parse_resume(json.dumps(escape_values(source)))
        self.assertEqual(parsed, source)
        rendered = cv.render(parsed)
        self.assertIn("Employer 2", rendered)
        self.assertIn("Qualification 2", rendered)
        self.assertEqual(rendered.count("GPA: 3.8/4.0"), 3)
        self.assertIn(r"reducing runtime by 42\%.", rendered)

    def test_latex_literals_round_trip_without_loss_or_double_escaping(self):
        literal = r"80% R&D $100 data_set C# {value} ~ ^ C:\path"
        source = sample_resume()
        source["experience"][0]["bullets"] = [literal]
        for escaped in (False, True):
            with self.subTest(escaped=escaped):
                data = escape_values(source) if escaped else source
                parsed = cv.parse_resume(json.dumps(data))
                self.assertEqual(parsed["experience"][0]["bullets"], [literal])
                self.assertIn(r"\item " + cv.tex(literal), cv.render(parsed))
        # Decode once: a literal backslash followed by % must retain both.
        self.assertEqual(cv.plain(cv.tex(r"\%")), r"\%")

    def test_unknown_latex_commands_are_rendered_as_literal_text(self):
        source = sample_resume()
        source["summary"] = r"\input{unexpected.tex}"
        parsed = cv.parse_resume(json.dumps(source))
        rendered = cv.render(parsed)
        self.assertNotIn(r"\input{unexpected.tex}", rendered)
        self.assertIn(r"\textbackslash{}input\{unexpected.tex\}", rendered)

    def test_model_typography_commands_are_normalized_before_rendering(self):
        source = sample_resume()
        source["education"][0]["dates"] = r"2022 \-- 2026"
        source["education"][0]["details"] = (
            r"Reuters' \textquotedblleft Europe ranking\textquotedblright; "
            r"\textquoteleft verified\textquoteright \textendash complete."
        )
        parsed = cv.parse_resume(json.dumps(source))
        self.assertEqual(parsed["education"][0]["dates"], "2022 -- 2026")
        self.assertEqual(
            parsed["education"][0]["details"],
            "Reuters' “Europe ranking”; ‘verified’ – complete.",
        )
        rendered = cv.render(parsed)
        self.assertNotIn("textquotedbl", rendered)
        self.assertNotIn(r"\textbackslash{}--", rendered)
        self.assertIn("Reuters' ``Europe ranking''; `verified' -- complete.", rendered)

    def test_model_latex_and_unicode_artifacts_are_normalized(self):
        source = sample_resume()
        source["name"] = r"C\'{e}sar Villegas"
        source["experience"][0]["dates"] = r"Sept 2025 \u2013 June 2026"
        source["experience"][0]["bullets"] = [
            r"Integrated relational databases \(PostgreSQL\) and \textit{ETL workflows}."
        ]
        source["education"][0]["institution"] = r"Universidad Aut\'{o}noma \(UAM\)"
        parsed = cv.parse_resume(json.dumps(source))
        self.assertEqual(parsed["name"], "César Villegas")
        self.assertEqual(parsed["experience"][0]["dates"], "Sept 2025 – June 2026")
        self.assertEqual(
            parsed["experience"][0]["bullets"],
            ["Integrated relational databases (PostgreSQL) and ETL workflows."],
        )
        self.assertEqual(parsed["education"][0]["institution"],
                         "Universidad Autónoma (UAM)")
        rendered = cv.render(parsed)
        for artifact in (r"\textbackslash{}'", "u2013", r"\textbackslash{}textit"):
            self.assertNotIn(artifact, rendered)

    def test_contact_escaping_preserves_link_values(self):
        source = sample_resume()
        parsed = cv.parse_resume(json.dumps(escape_values(source)))
        self.assertEqual(parsed["contact"], source["contact"])
        rendered = cv.render(parsed)
        self.assertIn(r"\href{https://example.com/a\_b?x=1\&y=2\#section}", rendered)
        self.assertIn(r"\href{https://example.com/a\%20b}", rendered)
        self.assertIn(r"\href{mailto:first\_last+tag@example.com}", rendered)

    def test_renderer_uses_compact_single_page_template(self):
        rendered = cv.render(cv.parse_resume(json.dumps(sample_resume())))
        self.assertIn(r"\documentclass[10pt,a4paper]{extarticle}", rendered)
        self.assertIn(r"top=0.35in,bottom=0.35in", rendered)
        self.assertIn(r"\linespread{0.96}", rendered)
        self.assertIn(r"itemsep=0pt", rendered)

    def test_renderer_uses_requested_section_names_and_order(self):
        rendered = cv.render(cv.parse_resume(json.dumps(sample_resume())))
        headings = re.findall(r"^\\cvsection\{(.+?)\}$", rendered, re.MULTILINE)
        self.assertEqual(headings, [
            "Profile",
            "Work Experience",
            "Education",
            r"Projects \& Awards",
            "Skills",
            "Languages",
        ])
        self.assertNotIn(r"\cvsection{Experience}", rendered)
        self.assertNotIn(r"\cvsection{Selected Projects}", rendered)
        self.assertNotIn(r"\cvsection{Technical Skills}", rendered)

    def test_final_pdf_name_is_normalized_and_rejects_paths(self):
        self.assertEqual(cv.normalized_pdf_name("candidate_cv"), "candidate_cv.pdf")
        self.assertEqual(cv.normalized_pdf_name("candidate_cv.PDF"), "candidate_cv.PDF")
        for invalid in ("", "../candidate.pdf", r"folder\candidate.pdf", "candidate.docx"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                cv.normalized_pdf_name(invalid)

    def test_compile_and_copy_pdf_uses_pdflatex_and_output_cv_name(self):
        tex_file = Path("generated/revolut_python_cv.tex")

        def fake_run(command, **kwargs):
            self.assertIn("-no-shell-escape", command)
            return SimpleNamespace(
                returncode=0,
                stdout="Output written on intermediate.pdf (1 page, 123 bytes).",
            )

        with patch.object(cv.shutil, "which", return_value="pdflatex"), \
             patch.object(cv.subprocess, "run", side_effect=fake_run), \
             patch.object(cv.shutil, "copy2") as copy_pdf, \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "mkdir"):
            destination = cv.compile_and_copy_pdf(
                tex_file, "final_candidate_cv", Path("tmp")
            )

        expected = (Path("tmp") / "final_candidate_cv.pdf").resolve()
        self.assertEqual(destination, expected)
        copy_pdf.assert_called_once_with(tex_file.resolve().with_suffix(".pdf"),
                                         Path("tmp") / "final_candidate_cv.pdf")

    def test_multi_page_pdf_is_not_copied_to_output_cv(self):
        tex_file = Path("generated/revolut_python_cv.tex")
        result = SimpleNamespace(
            returncode=0,
            stdout="Output written on intermediate.pdf (2 pages, 456 bytes).",
        )
        with patch.object(cv.shutil, "which", return_value="pdflatex"), \
             patch.object(cv.subprocess, "run", return_value=result), \
             patch.object(cv.shutil, "copy2") as copy_pdf, \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "mkdir"):
            with self.assertRaisesRegex(RuntimeError, "exactly one page"):
                cv.compile_and_copy_pdf(tex_file, "final_candidate_cv", Path("tmp"))
        copy_pdf.assert_not_called()

    def test_schema_errors_are_rejected_instead_of_silently_losing_data(self):
        source = sample_resume()
        missing = copy.deepcopy(source)
        del missing["education"]
        extra = dict(source, audit="private notes")
        wrong_list = dict(source, experience="not an array")
        wrong_scalar = dict(source, name=None)
        missing_nested = copy.deepcopy(source)
        del missing_nested["education"][0]["details"]
        for data in (missing, extra, wrong_list, wrong_scalar, missing_nested, []):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    cv.parse_resume(json.dumps(data))
        with self.assertRaises(ValueError):
            cv.parse_resume('```json\n{}\n```')

    @patch.object(gemini, "urlopen")
    def test_request_sends_system_prompt_and_strict_json_mode(self, urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": "{}"}]},
        }]}).encode()
        urlopen.return_value.__enter__.return_value = response
        cv.call_gemini("dummy-test-key", cv.prompt("Example offer", "Example profile"), cv.MODEL)
        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], cv.SYSTEM)
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")

    @patch.object(gemini, "urlopen")
    def test_token_limited_response_is_rejected_even_if_valid_json(self, urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({"candidates": [{
            "finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{}"}]},
        }]}).encode()
        urlopen.return_value.__enter__.return_value = response
        with self.assertRaisesRegex(RuntimeError, "incomplete CV"):
            cv.call_gemini("dummy-test-key", "Example", cv.MODEL)


if __name__ == "__main__":
    unittest.main()

