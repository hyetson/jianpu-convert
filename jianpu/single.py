"""Reusable one-instrument, one-staff:voice conversion workflow."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import uuid

from .pipeline import PROJECT, build

XML_SUFFIXES = {".xml", ".musicxml", ".mxl"}
FAMILIES = {"wind", "bowed", "plucked", "struck-string", "unknown"}


def prepare_config(source: Path, output: Path, profile: Path, *, musicxml: Path | None = None,
                   instrument_name: str = "单乐器", instrument_family: str = "unknown", part_id: str = "solo",
                   xml_part: str | None = None, title: str | None = None, composer: str | None = None,
                   workflow: str = 'single-voice', primary_voice: str | None = None) -> tuple[dict, list[Path] | None]:
    if workflow not in ('single-voice','local-dual-voice'): raise ValueError('Invalid one-instrument workflow')
    if primary_voice is not None and workflow!='local-dual-voice': raise ValueError('Primary voice is only used in dual mode')
    source, output, profile = source.resolve(), output.resolve(), profile.resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    if source.suffix.lower() not in XML_SUFFIXES | {".pdf"}:
        raise ValueError("Single-voice input must be PDF, MusicXML/XML or MXL; MIDI is not implemented")
    if output.suffix.lower() != ".pdf": raise ValueError("Output must have a .pdf extension")
    if output == source: raise ValueError("Output must not overwrite the input")
    if instrument_family not in FAMILIES: raise ValueError("Unknown instrument family")
    if not part_id.strip() or not instrument_name.strip(): raise ValueError("Part ID and instrument name must be nonempty")
    config = json.loads(profile.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict): raise ValueError("Profile must be a JSON object")
    # Paths in a reusable profile are relative to that profile, independent of cwd.
    fonts = config.get("fonts", {})
    for name, value in list(fonts.items()):
        def absolute(v):
            p = Path(v)
            return str(p.resolve() if p.is_absolute() else (profile.parent / p).resolve())
        fonts[name] = [absolute(v) for v in value] if isinstance(value, list) else absolute(value)
    part = {"id": part_id, "name": instrument_name, "instrumentFamily": instrument_family}
    if config.get('instrumentProfileId') is not None: part['instrumentProfileId'] = config['instrumentProfileId']
    if xml_part: part["musicxmlPart"] = xml_part
    if source.suffix.lower() == ".pdf":
        part["pdf"] = str(source)
        xml_inputs = [musicxml.resolve()] if musicxml else None
    else:
        if musicxml is not None: raise ValueError("--musicxml is only used with a PDF input")
        xml_inputs = [source]
    if xml_inputs and not xml_inputs[0].is_file(): raise FileNotFoundError(xml_inputs[0])
    if xml_inputs and xml_inputs[0].suffix.lower() not in XML_SUFFIXES: raise ValueError("Reviewed input must be MusicXML/XML or MXL")
    if primary_voice is not None: config.setdefault('localVoices', {})['primaryVoice']=primary_voice
    config.update({"workflow": workflow, "parts": [part], "output": str(output),
                   "title": title if title is not None else source.stem,
                   "composer": composer if composer is not None else config.get("composer", ""),
                   "profileSource": str(profile)})
    return config, xml_inputs


def convert_single(source: Path, output: Path, *, profile: Path = PROJECT / "configs/single-voice.json",
                   musicxml: Path | None = None, instrument_name: str = "单乐器", instrument_family: str = "unknown",
                   part_id: str = "solo", xml_part: str | None = None, title: str | None = None, composer: str | None = None,
                   audiveris: str | None = None, node_executable: str | None = None, draft: bool = False,
                   overwrite: bool = False, timeout: int = 1200,
                   workflow: str = 'single-voice', primary_voice: str | None = None) -> dict:
    config, xml_inputs = prepare_config(source, output, profile, musicxml=musicxml, instrument_name=instrument_name,
        instrument_family=instrument_family, part_id=part_id, xml_part=xml_part, title=title, composer=composer,
        workflow=workflow,primary_voice=primary_voice)
    name = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    folder = PROJECT / ('tmp/dual-voice' if workflow=='local-dual-voice' else 'tmp/single-voice') / name
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / "config.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    report = build(path, xml_inputs=xml_inputs, audiveris=audiveris, node_executable=node_executable,
                   draft=draft, overwrite=overwrite, timeout=timeout)
    report["resolvedConfig"] = str(path)
    return report
