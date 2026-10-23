from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from .model import Issue
from .musicxml import align_parts, parse_part
from .pdf_evidence import repair_rest_counts
from .instruments import resolve_instrument_profile, describe_texture

PROJECT = Path(__file__).resolve().parents[1]


def resolve_path(value: str, base: Path = PROJECT) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def find_audiveris(explicit: str | None = None) -> Path | None:
    value = explicit or os.environ.get("AUDIVERIS_EXE")
    if value:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Audiveris executable not found: {path}")
        return path
    for name in ("Audiveris", "audiveris"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for path in (PROJECT / "tools" / "audiveris" / "Audiveris.exe",
                 Path("C:/Program Files/Audiveris/Audiveris.exe"),
                 Path("E:/ProSoftware/Audiveris/Audiveris.exe")):
        if path.is_file():
            return path
    return None


def doctor() -> dict:
    try:
        audiveris = find_audiveris()
    except FileNotFoundError:
        audiveris = None
    packages = {name: importlib.util.find_spec(name) is not None
                for name in ("music21", "pdfplumber", "pypdfium2", "PIL")}
    return {
        "python": sys.version.split()[0], "pythonExecutable": sys.executable,
        "pythonPackages": packages, "node": shutil.which("node"),
        "typescript": (PROJECT / "node_modules/typescript/bin/tsc").is_file(),
        "pdfkit": (PROJECT / "node_modules/pdfkit/package.json").is_file(),
        "compiledRenderer": (PROJECT / "dist/render.js").is_file(),
        "audiveris": str(audiveris) if audiveris else None,
        "bravura": (PROJECT / "tools/fonts/Bravura.otf").is_file(),
    }


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def transcribe(pdf: Path, executable: Path, folder: Path, timeout: int) -> Path:
    folder.mkdir(parents=True, exist_ok=False)
    log = folder / "audiveris.log"
    command = [str(executable), "-batch", "-transcribe", "-save", "-export",
               "-constant", "org.audiveris.omr.text.Language.defaultSpecification=eng",
               "-output", str(folder), "--", str(pdf)]
    runtime_temp = folder / "tmp"
    runtime_temp.mkdir()
    environment = os.environ.copy()
    environment.update({"TEMP": str(runtime_temp), "TMP": str(runtime_temp)})
    appdata = PROJECT / "tmp/audiveris-appdata"
    native_cache = PROJECT / "tmp/javacpp-cache"
    pdf_font_cache = PROJECT / "tmp/pdfbox-fontcache"
    appdata.mkdir(parents=True, exist_ok=True)
    native_cache.mkdir(parents=True, exist_ok=True)
    pdf_font_cache.mkdir(parents=True, exist_ok=True)
    # Audiveris and JavaCPP otherwise write outside the project, even in batch
    # mode. These settings affect this child process only, never system values.
    if os.name == "nt":
        environment["APPDATA"] = str(appdata)
    environment["JAVA_TOOL_OPTIONS"] = (
        f'-Dorg.bytedeco.javacpp.cachedir="{native_cache}" '
        f'-Dpdfbox.fontcache="{pdf_font_cache}" '
        f'-Djava.io.tmpdir="{runtime_temp}"'
    )
    tessdata = PROJECT / "tools/tessdata"
    if (tessdata / "eng.traineddata").is_file():
        environment["TESSDATA_PREFIX"] = str(tessdata)
    print(f"OMR: {pdf.name}", flush=True)
    with log.open("w", encoding="utf-8") as stream:
        try:
            completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                       timeout=timeout, check=False, env=environment,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Audiveris timed out after {timeout}s; inspect {log}") from exc
    if completed.returncode:
        raise RuntimeError(f"Audiveris exit {completed.returncode}; inspect {log}")
    candidates = sorted(folder.rglob("*.mxl"))
    if not candidates:
        candidates = sorted(folder.rglob("*.musicxml")) + sorted(folder.rglob("*.xml"))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one MusicXML score, found {len(candidates)} in {folder}; inspect {log}")
    (folder / "source.json").write_text(json.dumps({"source": str(pdf), "sha256": sha256(pdf),
                                                  "command": command}, ensure_ascii=False, indent=2), encoding="utf-8")
    return candidates[0]


def music21_check(path: Path, part_id: str, issues: list[Issue]) -> dict:
    """Independent diagnostic, not a destructive score rewrite."""
    try:
        from music21 import converter
        score = converter.parse(str(path), forceSource=True)
        return {"parts": len(score.parts), "notesAndRests": len(score.recurse().notesAndRests)}
    except ImportError:
        issues.append(Issue("warning", "music21_unavailable", part_id, "",
                            "music21 not installed; independent import validation skipped"))
    except Exception as exc:
        issues.append(Issue("warning", "music21_import", part_id, "", f"Independent import diagnostic: {exc}"))
    return {}


def build(config_file: Path, *, xml_inputs: list[Path] | None = None,
          audiveris: str | None = None, draft: bool = False, overwrite: bool = False,
          timeout: int = 1200, node_executable: str | None = None) -> dict:
    config = json.loads(config_file.read_text(encoding="utf-8-sig"))
    configs = config.get("parts", [])
    if not configs or len({p["id"] for p in configs}) != len(configs):
        raise ValueError("Config requires parts with distinct IDs")
    workflow = config.get("workflow", "general")
    if workflow not in ("general", "single-voice", "local-dual-voice"):
        raise ValueError("workflow must be general, single-voice or local-dual-voice")
    if workflow in ("single-voice", "local-dual-voice") and len(configs) != 1:
        raise ValueError(f"{workflow} workflow requires exactly one part")
    profiles = {}
    for spec in configs:
        if spec.get("instrumentFamily", "unknown") not in ("wind", "bowed", "plucked", "struck-string", "unknown"):
            raise ValueError(f"Invalid instrumentFamily for {spec['id']}")
        profiles[spec['id']] = resolve_instrument_profile(spec.get('instrumentProfileId'), spec.get('instrumentFamily', 'unknown'))
    if config.get("pitchPolicy", "written") != "written":
        raise ValueError("Initial version supports written pitch only; sounding-pitch conversion is not enabled")
    output = resolve_path(config["output"])
    protected = {p.resolve() for p in (PROJECT / "example").glob("*.pdf")}
    protected.update(resolve_path(p["pdf"]) for p in configs if "pdf" in p)
    if output in protected:
        raise ValueError("Output cannot overwrite any input/reference PDF")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {output}; use --overwrite for a generated output")
    if xml_inputs and len(xml_inputs) != len(configs):
        raise ValueError("Supply one MusicXML per configured part, in the same order")
    executable = None
    if xml_inputs is None:
        executable = find_audiveris(audiveris)
        if executable is None:
            raise RuntimeError("Audiveris missing. Install only after user approval, then pass --audiveris PATH.")
        for spec in configs:
            if not resolve_path(spec["pdf"]).is_file():
                raise FileNotFoundError(spec["pdf"])
    fonts = {}
    for name, value in config.get("fonts", {}).items():
        if isinstance(value, list):
            if name not in ("restCounts", "measureNumbers") or not value:
                raise ValueError("Only fonts.restCounts and fonts.measureNumbers accept nonempty font-path lists")
            fonts[name] = [str(resolve_path(v)) for v in value]
        else:
            fonts[name] = str(resolve_path(value))
    for name in ("text", "music"):
        if name not in fonts:
            raise FileNotFoundError(f"Missing {name} font; configure fonts.{name}")
    for name, value in fonts.items():
        for font_path in value if isinstance(value, list) else [value]:
            if not Path(font_path).is_file():
                raise FileNotFoundError(f"Missing {name} font; configure fonts.{name}")
    node = node_executable or os.environ.get("JIANPU_NODE") or shutil.which("node")
    if node is not None:
        node = shutil.which(node) or (str(Path(node).resolve()) if Path(node).is_file() else None)
    renderer = PROJECT / "dist/render.js"
    if node is None or not renderer.is_file():
        raise RuntimeError("Node or compiled renderer missing; after dependency approval, run npm run build")
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    run = output.parent / "runs" / run_id
    run.mkdir(parents=True, exist_ok=False)
    issues: list[Issue] = []
    parts, diagnostics, sources = [], {}, []
    try:
        for ix, spec in enumerate(configs):
            if xml_inputs:
                xml = xml_inputs[ix].resolve()
                if not xml.is_file():
                    raise FileNotFoundError(xml)
            else:
                assert executable
                xml = transcribe(resolve_path(spec["pdf"]), executable, run / spec["id"], timeout)
                xml = repair_rest_counts(resolve_path(spec["pdf"]), xml, run / spec["id"], spec["id"], issues)
            source = {"part": spec["id"], "musicxml": str(xml), "sha256": sha256(xml)}
            if spec.get("pdf") and resolve_path(spec["pdf"]).is_file():
                pdf = resolve_path(spec["pdf"])
                source.update({"pdf": str(pdf), "pdfSha256": sha256(pdf)})
            sources.append(source)
            parts.append(parse_part(xml, spec["id"], spec["name"], issues, spec.get("musicxmlPart")))
            parts[-1].instrument_family = spec.get("instrumentFamily", "unknown")
            parts[-1].instrument_profile = profiles[spec['id']]
            if profiles[spec['id']] is not None and parts[-1].instrument_family == 'unknown':
                parts[-1].instrument_family = profiles[spec['id']]['family']
            parts[-1].texture_summary = describe_texture(parts[-1])
            if workflow == "single-voice":
                voices = sorted({e.voice for m in parts[-1].measures for e in m.events})
                if len(voices) != 1:
                    raise ValueError(f"Single-voice workflow found {len(voices)} staff:voice streams ({', '.join(voices)}); correct/select the source explicitly before rendering")
            if workflow == "local-dual-voice":
                voices = {e.voice for m in parts[-1].measures for e in m.events}
                if not 1 <= len(voices) <= 2:
                    raise ValueError(f"Local dual-voice workflow requires 1-2 staff:voice streams; found {len(voices)}")
                primary = config.get('localVoices', {}).get('primaryVoice')
                if primary is not None and primary not in voices:
                    raise ValueError(f"Primary voice {primary} is absent; available: {', '.join(sorted(voices))}")
            diagnostics[spec["id"]] = music21_check(xml, spec["id"], issues)
        bars = align_parts(parts, issues)
        report = {"run": run_id, "sources": sources, "music21": diagnostics,
                  "issues": [asdict(i) for i in issues],
                  "errors": sum(i.severity == "error" for i in issues),
                  "warnings": sum(i.severity == "warning" for i in issues)}
        report_path = run / "report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        score = {"schemaVersion": 1, "title": config.get("title", "简谱"),
                 "subtitle": config.get("subtitle", ""), "composer": config.get("composer", ""),
                 "pitchPolicy": "written", "draft": draft, "recognitionSource": xml_inputs is None,
                 "parts": [p.to_json() for p in parts], "bars": bars,
                 "layout": config.get("layout", {}), "fonts": fonts,
                 "techniques": config.get("techniques", {}),
                 "workflow": workflow,"dynamicsPlacement": config.get("dynamicsPlacement", "below"),
                 "localVoices": config.get("localVoices", {}),
                 "issues": report["issues"]}
        score_path = run / "score.json"
        score_path.write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
        if report["errors"] and not draft:
            raise RuntimeError(f"{report['errors']} semantic/alignment errors; no PDF produced. Review {report_path}; --draft explicitly permits a marked review copy.")
        temporary_pdf = run / "rendered.pdf"
        print(f"Render: {len(bars)} bars, {len(parts)} parts", flush=True)
        render_log = run / "render.log"
        with render_log.open("w", encoding="utf-8") as stream:
            try:
                subprocess.run([node, str(renderer), str(score_path), str(temporary_pdf)],
                               cwd=PROJECT, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=120)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError(f"Renderer failed; inspect {render_log}") from exc
        if not temporary_pdf.is_file() or temporary_pdf.stat().st_size < 100:
            raise RuntimeError("Renderer did not produce a PDF")
        render_report = temporary_pdf.with_suffix(".render.json")
        if render_report.is_file():
            report["render"] = json.loads(render_report.read_text(encoding="utf-8"))
            for warning in report["render"].get("warnings", []):
                report["issues"].append(asdict(Issue("warning", "render_review", "all", "", warning)))
            report["warnings"] = sum(i["severity"] == "warning" for i in report["issues"])
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(temporary_pdf, output)
        report.update({"pdf": str(output), "score": str(score_path), "report": str(report_path)})
        report["workflow"] = workflow
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    except Exception as exc:
        (run / "failure.json").write_text(json.dumps({"error": str(exc), "sources": sources,
                                                      "issues": [asdict(i) for i in issues]}, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
