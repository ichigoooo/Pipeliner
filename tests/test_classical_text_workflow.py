from __future__ import annotations

from pathlib import Path
from typing import cast

from pipeliner.persistence.repositories import WorkflowRepository
from pipeliner.services.workflow_service import WorkflowService


def test_classical_text_workflow_uses_chunked_outline_pipeline() -> None:
    service = WorkflowService(cast(WorkflowRepository, None))
    spec_path = Path("projects/classical-text-to-csv/workflow.json")

    raw_spec = service.load_raw_file(spec_path)
    spec, _warnings = service.validate_spec(raw_spec)

    assert spec.metadata.workflow_id == "classical-text-to-csv"
    assert spec.metadata.version == "0.5.1"

    nodes = {node.node_id: node for node in spec.nodes}
    assert "text_chunking" in nodes
    assert "chapter_outline_scan" in nodes
    assert "chapter_structure_finalize" in nodes
    assert "chapter_batch_segmentation" in nodes

    text_chunking = nodes["text_chunking"]
    assert text_chunking.depends_on == ["text_preprocessing"]
    assert [item.name for item in text_chunking.outputs] == [
        "text_chunks_dir",
        "chunk_manifest",
    ]
    assert text_chunking.executor.skill == "text-chunking"

    chapter_outline_scan = nodes["chapter_outline_scan"]
    assert chapter_outline_scan.depends_on == ["text_chunking"]
    assert [item.name for item in chapter_outline_scan.inputs] == [
        "text_chunks_dir",
        "chunk_manifest",
        "structure_hint",
    ]

    chapter_structure_finalize = nodes["chapter_structure_finalize"]
    assert chapter_structure_finalize.depends_on == [
        "text_preprocessing",
        "text_chunking",
        "chapter_outline_scan",
    ]
    assert [item.name for item in chapter_structure_finalize.outputs] == [
        "chapters_structure",
        "chapter_files_dir",
    ]
