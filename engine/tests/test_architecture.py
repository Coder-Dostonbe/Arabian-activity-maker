"""Guards for architectural rules: the engine stays framework- and provider-free."""

import ast
from pathlib import Path

import arabmorph
from arabmorph import RULES, Lexicon

PACKAGE_DIR = Path(arabmorph.__file__).parent
FORBIDDEN = {"django", "rest_framework", "celery", "redis", "openai", "anthropic", "requests", "httpx"}


def test_engine_imports_only_stdlib_and_itself():
    offenders = []
    for path in PACKAGE_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            offenders += [(path.name, n) for n in names if n.split(".")[0] in FORBIDDEN]
    assert offenders == []


def test_every_rule_has_bilingual_explanation_and_reference():
    for rule in RULES.values():
        assert rule.explanation("ar") and rule.explanation("en"), rule.id
        assert rule.reference and rule.example, rule.id
        assert 0 < rule.confidence <= 1, rule.id


def test_seed_lexicon_loads_from_package_data():
    lex = Lexicon.seed()
    assert len(lex) >= 10
    assert all(not e.verified for e in lex.lookup("عصا"))
