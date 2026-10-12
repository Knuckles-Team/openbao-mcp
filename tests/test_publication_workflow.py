"""Keep docs pushes separate from guarded package publication."""

from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "ed8ea8ac5989cbc883c149843b311aeecb44e6a2"


def _workflow(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def _push_matches(workflow, ref):
    # PyYAML's YAML 1.1 reader represents the Actions "on" key as True.
    push = workflow[True]["push"]
    kind, name = ref.removeprefix("refs/").split("/", 1)
    filters = push.get({"heads": "branches", "tags": "tags"}[kind], [])
    return any(fnmatchcase(name, pattern) for pattern in filters)


@pytest.mark.parametrize(
    "ref, expected",
    [
        ("refs/tags/v2.1.0", True),
        ("refs/tags/v2.2.0rc1", True),
        ("refs/heads/main", False),
        ("refs/heads/docs-update", False),
        ("refs/tags/docs-preview", False),
    ],
)
def test_only_release_tags_start_package_publication(ref, expected):
    assert _push_matches(_workflow("pipeline.yml"), ref) is expected


def test_each_package_publisher_uses_reviewed_contract():
    jobs = _workflow("pipeline.yml")["jobs"]
    assert set(jobs) == {"publish-pypi", "publish-docker"}
    for job, workflow in [
        ("publish-pypi", "python_pipeline"),
        ("publish-docker", "container_pipeline"),
    ]:
        assert jobs[job]["uses"] == (
            f"Knuckles-Team/pipelines/.github/workflows/{workflow}.yml@{CONTRACT}"
        )
        assert "if" not in jobs[job]
        assert not jobs[job].get("continue-on-error", False)
    assert jobs["publish-docker"]["needs"] == "publish-pypi"


def test_pages_keeps_shared_main_and_spec_triggers():
    workflow = _workflow("pages.yml")
    publisher = workflow["jobs"]["publish-pages"]
    assert publisher["uses"].endswith("/pages_pipeline.yml@main")
    assert publisher["with"]["spec_dashboard_enabled"] is True
    assert "specs/**" in workflow[True]["push"]["paths"]
    assert ".github/spec-dashboard.json" in workflow[True]["push"]["paths"]


def test_release_hook_inherits_catalogue_policy():
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    matches = [
        (repo, hook)
        for repo in config["repos"]
        for hook in repo["hooks"]
        if hook["id"] == "dependency-readiness"
    ]
    assert len(matches) == 1
    repo, hook = matches[0]
    assert repo["repo"] == "https://github.com/Knuckles-Team/pipelines"
    assert repo["rev"] == CONTRACT
    assert hook == {"id": "dependency-readiness"}


def test_alternate_docs_job_keeps_validation_without_publication():
    workflow = _workflow("docs.yml")
    assert workflow[True] == {
        "push": {"branches": ["main"]},
        "workflow_dispatch": None,
    }
    assert workflow["permissions"] == {"contents": "write"}
    assert set(workflow["jobs"]) == {"deploy-docs"}
    job = workflow["jobs"]["deploy-docs"]
    assert job["runs-on"] == "ubuntu-latest"
    assert [step.get("run") for step in job["steps"] if "run" in step] == [
        "pip install mkdocs-material",
        "mkdocs build",
    ]
    assert all(
        "gh-deploy" not in path.read_text()
        for path in (ROOT / ".github/workflows").glob("*.yml")
    )
