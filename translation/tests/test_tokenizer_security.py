"""Tokenizer-only integration checks. No model weights, inference or training are loaded."""
from __future__ import annotations

import importlib.util
from importlib.metadata import distribution
import inspect
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from transformers import PreTrainedTokenizerFast, ProcessorMixin
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from translation._tokenizer_security import _install_chat_template_save_guard

_TOKENIZER_SAVE = PreTrainedTokenizerBase.save_pretrained
_PROCESSOR_SAVE = ProcessorMixin.save_pretrained


@pytest.fixture(autouse=True)
def fresh_serializers(monkeypatch):
    monkeypatch.setattr(PreTrainedTokenizerBase, "save_pretrained", _TOKENIZER_SAVE)
    monkeypatch.setattr(ProcessorMixin, "save_pretrained", _PROCESSOR_SAVE)


def tokenizer(template=None):
    return PreTrainedTokenizerFast(
        tokenizer_object=Tokenizer(WordLevel({"[UNK]": 0, "hello": 1}, unk_token="[UNK]")),
        unk_token="[UNK]",
        chat_template=template,
    )


@pytest.mark.parametrize("kind", ["tokenizer", "processor"])
@pytest.mark.parametrize("name", [
    "../../escape", "{absolute}", "..\\escape", "C:\\escape", "C:escape",
    "normal/child", "normal\\child", ".", "..", "", "null\0name", "normal:stream", 1,
])
def test_real_serializers_reject_unsafe_names_before_writing(tmp_path, kind, name):
    if name == "{absolute}":
        name = str(tmp_path / "absolute-escape")
    obj = tokenizer({"default": "normal", name: "attacker"}) if kind == "tokenizer" else ProcessorMixin(
        chat_template={"default": "normal", name: "attacker"}
    )
    _install_chat_template_save_guard()
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Invalid chat template name"):
        obj.save_pretrained(output)
    assert not output.exists()
    assert not (tmp_path / "escape.jinja").exists()


@pytest.mark.parametrize("kind", ["tokenizer", "processor"])
def test_real_serializers_preserve_templates_return_and_reload(tmp_path, kind):
    templates = {"default": "normal", "tool_use": "tools", "friendly name": "spaces", "工具": "unicode"}
    obj = tokenizer(templates) if kind == "tokenizer" else ProcessorMixin(chat_template=templates)
    original_signature = inspect.signature(type(obj).save_pretrained)
    _install_chat_template_save_guard()
    guarded_method = type(obj).save_pretrained
    _install_chat_template_save_guard()
    assert type(obj).save_pretrained is guarded_method
    assert inspect.signature(guarded_method) == original_signature
    output = tmp_path / "output"
    files = obj.save_pretrained(output)
    assert files
    assert all(Path(path).is_file() for path in files)
    assert sorted(p.read_text() for p in output.rglob("*.jinja")) == sorted(templates.values())
    if kind == "tokenizer":
        loaded = PreTrainedTokenizerFast.from_pretrained(output, local_files_only=True)
        assert loaded.chat_template == templates


def test_legacy_list_normalization_is_guarded(tmp_path):
    obj = tokenizer([{"name": "../../escape", "template": "attacker"}])
    assert isinstance(obj.chat_template, dict)
    _install_chat_template_save_guard()
    with pytest.raises(ValueError, match="Invalid chat template name"):
        obj.save_pretrained(tmp_path / "output")
    assert not (tmp_path / "output").exists()


def optimum_save_utils():
    # Execute the pinned serializer utility itself without importing model/Torch runtime code.
    source = distribution("optimum").locate_file("optimum/utils/save_utils.py")
    spec = importlib.util.spec_from_file_location("optimum_save_utils_fixture", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_actual_optimum_implicit_save_rejects_untrusted_legacy_config(tmp_path):
    source = tmp_path / "source"
    # Seed the legacy config before installing the guard, with no template file writes.
    tokenizer({"../../escape": "attacker"}).save_pretrained(source, save_jinja_files=False)
    save_utils = optimum_save_utils()
    _install_chat_template_save_guard()
    with pytest.raises(ValueError, match="Invalid chat template name"):
        save_utils.maybe_save_preprocessors(source, tmp_path / "output")
    assert not (tmp_path / "escape.jinja").exists()


def test_actual_optimum_implicit_processor_save_is_guarded(tmp_path, monkeypatch):
    save_utils = optimum_save_utils()
    processor = ProcessorMixin(chat_template={"../../escape": "attacker"})
    monkeypatch.setattr(save_utils, "maybe_load_preprocessors", lambda *args, **kwargs: [processor])
    _install_chat_template_save_guard()
    with pytest.raises(ValueError, match="Invalid chat template name"):
        save_utils.maybe_save_preprocessors(tmp_path / "source", tmp_path / "output")
    assert not (tmp_path / "escape.jinja").exists()


def test_actual_optimum_implicit_save_preserves_normal_templates(tmp_path):
    templates = {"default": "normal", "tool_use": "tools", "工具": "unicode"}
    source = tmp_path / "source"
    tokenizer(templates).save_pretrained(source)
    save_utils = optimum_save_utils()
    _install_chat_template_save_guard()
    output = tmp_path / "output"
    save_utils.maybe_save_preprocessors(source, output)
    assert sorted(p.read_text() for p in output.rglob("*.jinja")) == sorted(templates.values())


@pytest.mark.parametrize("entrypoint", ["tier2", "tier3", "train"])
def test_entrypoints_install_guard_before_implicit_saves(tmp_path, monkeypatch, entrypoint):
    obj = tokenizer({"../../escape": "attacker"})
    attempts = []

    class FakeOrtModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            # Optimum does this before returning, during its automatic temporary export.
            attempts.append("automatic export")
            obj.save_pretrained(tmp_path / "implicit-export")
            raise AssertionError("unsafe automatic export was not rejected")

    optimum = ModuleType("optimum")
    ort = ModuleType("optimum.onnxruntime")
    ort.ORTModelForFeatureExtraction = FakeOrtModel
    ort.ORTModelForSeq2SeqLM = FakeOrtModel
    monkeypatch.setitem(sys.modules, "optimum", optimum)
    monkeypatch.setitem(sys.modules, "optimum.onnxruntime", ort)

    if entrypoint == "tier2":
        from translation.tier2.embed import MiniLMEmbedder
        embedder = MiniLMEmbedder()
        embedder._model = object()
        invoke = lambda: embedder.export_onnx(tmp_path / "out" / "model.onnx")
    elif entrypoint == "tier3":
        from translation.tier3.export_onnx import export_onnx
        invoke = lambda: export_onnx(tmp_path / "checkpoint", tmp_path / "out", verbose=False)
    else:
        from translation.tier3.train import train

        class FakeDataset:
            @classmethod
            def from_list(cls, data):
                return cls()

            def map(self, *args, **kwargs):
                return self

        class FakeTrainer:
            def __init__(self, *args, **kwargs):
                pass

            def train(self):
                # Trainer saves its processing/collator tokenizer during epoch checkpointing.
                attempts.append("epoch checkpoint")
                obj.save_pretrained(tmp_path / "implicit-checkpoint")
                raise AssertionError("unsafe checkpoint was not rejected")

        monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
        monkeypatch.setitem(sys.modules, "datasets", SimpleNamespace(Dataset=FakeDataset))
        # A plain module avoids lazy model imports replacing these CPU-only collaborators.
        fake_transformers = ModuleType("transformers")
        fake_transformers.ProcessorMixin = ProcessorMixin
        fake_transformers.AutoTokenizer = SimpleNamespace(from_pretrained=lambda *a, **k: obj)
        fake_transformers.AutoModelForSeq2SeqLM = SimpleNamespace(from_pretrained=lambda *a, **k: object())
        fake_transformers.Seq2SeqTrainer = FakeTrainer
        fake_transformers.Seq2SeqTrainingArguments = lambda **kwargs: SimpleNamespace(**kwargs)
        fake_transformers.DataCollatorForSeq2Seq = lambda *a, **k: object()
        monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
        data = tmp_path / "data.jsonl"
        data.write_text((json.dumps({"english": "hello", "asl": "HELLO"}) + "\n") * 2_000)
        invoke = lambda: train(data, tmp_path / "out", verbose=False)

    with pytest.raises(ValueError, match="Invalid chat template name"):
        invoke()
    assert len(attempts) == 1
    assert not (tmp_path / "escape.jinja").exists()
