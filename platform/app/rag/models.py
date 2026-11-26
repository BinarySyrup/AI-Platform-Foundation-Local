from collections.abc import Iterable

from app.models.schemas import ModelSummary

EMBEDDING_MODEL = "nomic-embed-text:v1.5"


def chat_models(models: Iterable[ModelSummary]) -> list[ModelSummary]:
    return [model for model in models if model.name != EMBEDDING_MODEL]


def rag_aliases(model_names: Iterable[str]) -> dict[str, str]:
    names = list(dict.fromkeys(model_names))
    direct_names = set(names)
    aliases: dict[str, str] = {}
    for name in names:
        alias = f"{name}-rag"
        if alias not in direct_names:
            aliases[alias] = name
    return aliases
