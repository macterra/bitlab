"""Repository paths and source provenance, independent of the working directory."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def repo_path(relative):
    return ROOT / relative


def artifact_path(*parts):
    return ROOT.joinpath("artifacts", *parts)


def source_files(entry):
    """List the entry module and its local static imports, including packages.

    Paths are repository-relative and sorted so reports are reproducible. This
    accounts for implementation utilities too; it is not a language-size metric.
    """
    pending = [repo_path(entry).resolve()]
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        path.relative_to(ROOT)
        seen.add(path)
        for parent in path.parents:
            if parent == ROOT:
                break
            initializer = parent / "__init__.py"
            if initializer.is_file():
                pending.append(initializer)
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                     else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                module = ROOT.joinpath(*name.split("."))
                for candidate in (module.with_suffix(".py"), module / "__init__.py"):
                    if candidate.is_file():
                        pending.append(candidate.resolve())
                        break
    return sorted(path.relative_to(ROOT).as_posix() for path in seen)


def source_bytes(files):
    return b"".join(repo_path(name).read_bytes() for name in files)
