"""Explicit model-facing IDs; citation identity never depends on counting a list."""


def indexed_dossier(dossier):
    return dict(dossier, facts={f'fact_{i}': fact for i, fact in enumerate(dossier['facts'])})


def indexed_segments(segments):
    return {f'segment_{i}': segment for i, segment in enumerate(segments)}
