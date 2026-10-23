"""One instrument, up to two independent voices, expanded only where needed."""
from pathlib import Path
from .pipeline import PROJECT
from .single import convert_single


def convert_dual(source: Path, output: Path, **options) -> dict:
    options.setdefault('profile', PROJECT/'configs/dual-voice.json')
    return convert_single(source, output, workflow='local-dual-voice', **options)
