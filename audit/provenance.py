"""Provenance audit of the published ink-detection corpus.

Every published ink-detection artifact in the Vesuvius Challenge open data
carries, in the public catalogue, the id of the model that produced it and the
id of the volume it was run on. This module walks that catalogue and answers
three questions that matter before anyone trains or evaluates against those
labels:

  1. How many distinct models generated the published ink labels?
  2. At what energy / voxel size was each label actually computed -- as opposed
     to the energy of the grid it is finally displayed on?
  3. Is the sample an evaluation holdout for the generator, or is it listed in
     the generator's own ``compatible_samples``?

The catalogue lives at ``s3://vesuvius-challenge-open-data/metadata.json``.

GOTCHA (handled here): the object is gzip-compressed but served WITHOUT a
``Content-Encoding: gzip`` header, so an ordinary ``requests.get(...).json()``
fails. We sniff the magic bytes instead.
"""

from __future__ import annotations

import gzip
import json
import re
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field, asdict

S3_ROOT = "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/"
CATALOGUE_KEY = "metadata.json"

# Volume long ids embed their own acquisition parameters, e.g.
#   20250521125136-8.640um-1.2m-116keV-masked
_SCAN_RE = re.compile(
    r"(?P<um>[0-9]+(?:\.[0-9]+)?)um"
    r"(?:-(?P<prop>[0-9]+(?:\.[0-9]+)?)m)?"
    r"-(?P<kev>[0-9]+(?:\.[0-9]+)?)keV"
)


def load_catalogue(path_or_none=None, timeout=120):
    """Return the parsed public catalogue.

    ``path_or_none`` may be a local copy; otherwise the live object is fetched.
    Handles the undeclared gzip encoding.
    """
    if path_or_none:
        with open(path_or_none, "rb") as fh:
            raw = fh.read()
    else:
        req = urllib.request.Request(
            S3_ROOT + CATALOGUE_KEY, headers={"User-Agent": "vesuvius-uncertainty-bench"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    if raw[:2] == b"\x1f\x8b":  # gzip magic, served without Content-Encoding
        raw = gzip.decompress(raw)
    return json.loads(raw)


def parse_scan_params(long_id):
    """Extract (voxel_um, energy_keV) from a volume long id. None if absent."""
    if not long_id:
        return None, None
    m = _SCAN_RE.search(long_id)
    if not m:
        return None, None
    return float(m.group("um")), float(m.group("kev"))


@dataclass
class InkArtifact:
    """One published ink-detection output and its full provenance chain."""

    sample: str
    segment: str
    model_id: str
    target_volume: str
    target_volume_long_id: str = ""
    voxel_um: float | None = None
    energy_kev: float | None = None
    path: str = ""

    @property
    def above_100kev(self):
        return self.energy_kev is not None and self.energy_kev > 100.0


@dataclass
class ModelRecord:
    model_id: str
    long_id: str = ""
    architecture: str = ""
    target_resolution_um: tuple | None = None
    compatible_samples: list = field(default_factory=list)
    n_artifacts: int = 0
    samples: list = field(default_factory=list)


def _volume_long_ids(sample_entry):
    """Map volume id -> long id for one sample."""
    out = {}
    for vid, v in (sample_entry.get("volumes") or {}).items():
        out[vid] = v.get("long_id") or vid
    return out


def collect_ink_artifacts(catalogue, samples=None):
    """Walk the catalogue and return every published ink-detection artifact.

    Only the full-resolution ``ink-detection`` type is collected; the
    ``ink-detection-downsampled`` JPEG previews derive from it and would
    double-count.
    """
    found = []
    for sample_id, sample in (catalogue.get("samples") or {}).items():
        if samples and sample_id not in samples:
            continue
        vol_long = _volume_long_ids(sample)
        for seg_id, seg in (sample.get("segments") or {}).items():
            for entry in seg.get("data") or []:
                if entry.get("type") != "ink-detection":
                    continue
                params = entry.get("parameters") or {}
                model_id = params.get("model_id") or ""
                target = params.get("target_volume") or ""
                long_id = vol_long.get(target, "")
                um, kev = parse_scan_params(long_id)
                if um is None:
                    # Fall back to the artifact filename, which repeats them.
                    origins = entry.get("origins") or [{}]
                    um, kev = parse_scan_params(origins[0].get("path", ""))
                path = (entry.get("origins") or [{}])[0].get("path", "")
                found.append(
                    InkArtifact(
                        sample=sample_id,
                        segment=seg_id,
                        model_id=model_id,
                        target_volume=target,
                        target_volume_long_id=long_id,
                        voxel_um=um,
                        energy_kev=kev,
                        path=path,
                    )
                )
    return found


def model_records(catalogue, artifacts):
    """Join artifacts against the catalogue's model registry."""
    counts = defaultdict(int)
    seen_samples = defaultdict(set)
    for a in artifacts:
        counts[a.model_id] += 1
        seen_samples[a.model_id].add(a.sample)

    out = {}
    models = catalogue.get("models") or {}
    for mid, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        m = models.get(mid) or {}
        props = m.get("properties") or {}
        lo, hi = props.get("target_resolution_um_min"), props.get("target_resolution_um_max")
        out[mid] = ModelRecord(
            model_id=mid,
            long_id=m.get("long_id", ""),
            architecture=props.get("architecture", ""),
            target_resolution_um=(lo, hi) if lo is not None else None,
            compatible_samples=props.get("compatible_samples") or [],
            n_artifacts=n,
            samples=sorted(seen_samples[mid]),
        )
    return out


def surface_grid_energies(catalogue, sample_id):
    """Energies at which a sample has published *surface volumes*.

    A label computed on a 2.215 um / 111 keV volume can still be shipped for a
    segment whose surface volumes exist at 116 keV: this is exactly the
    transfer that makes the label independent of the 116 keV signal, and it is
    the thing an evaluator must not confuse with "the label was measured at
    116 keV".
    """
    sample = (catalogue.get("samples") or {}).get(sample_id) or {}
    energies = set()
    for seg in (sample.get("segments") or {}).values():
        for entry in seg.get("data") or []:
            if entry.get("type") != "layers-zarr":
                continue
            path = (entry.get("origins") or [{}])[0].get("path", "")
            um, kev = parse_scan_params(path)
            if kev is not None:
                energies.add((um, kev))
    return sorted(energies)


def audit(catalogue, focus_samples=("PHerc0343P", "PHerc0500P2", "PHerc0139", "PHerc0009B")):
    """Full audit. Returns a JSON-serialisable dict."""
    artifacts = collect_ink_artifacts(catalogue)
    models = model_records(catalogue, artifacts)

    above = [a for a in artifacts if a.above_100kev]
    generators_above = sorted({a.model_id for a in above})

    # Which models produced labels for the samples that carry >100 keV surface
    # volumes -- the corpus anyone evaluating at 113/116 keV will actually use.
    corpus = {}
    for s in focus_samples:
        arts = [a for a in artifacts if a.sample == s]
        gens = sorted({a.model_id for a in arts})
        grids = surface_grid_energies(catalogue, s)
        corpus[s] = {
            "n_ink_artifacts": len(arts),
            "generator_model_ids": gens,
            "n_distinct_generators": len(gens),
            "label_computed_on": sorted(
                {(a.voxel_um, a.energy_kev) for a in arts if a.energy_kev}
            ),
            "surface_volume_grids": grids,
            "in_compatible_samples_of": [
                mid for mid in gens if s in (models.get(mid).compatible_samples if models.get(mid) else [])
            ],
        }

    return {
        "catalogue": {
            "n_samples": len(catalogue.get("samples") or {}),
            "n_models": len(catalogue.get("models") or {}),
        },
        "totals": {
            "n_ink_artifacts": len(artifacts),
            "n_distinct_generators": len({a.model_id for a in artifacts}),
            "n_ink_artifacts_computed_above_100kev": len(above),
            "generators_above_100kev": generators_above,
        },
        "models": {mid: asdict(rec) for mid, rec in models.items()},
        "focus_corpus": corpus,
    }
