"""
Tier 3: Fine-tune T5-small on English → ASL gloss.

Target:
  - Base model: t5-small (60M params)
  - Output: ONNX INT8 < 20MB
  - Inference target: < 200ms on Snapdragon 600 via NNAPI
  - Ships as "experimental" in V1 — requires sufficient parallel data

Data requirements:
  - Minimum ~2,000 parallel sentence pairs to see meaningful improvement
  - Below that threshold, ship V1 with Tiers 1+2 only (per spec)

Input format (from data pipeline):
  English sentence → ASL gloss string (space-separated tokens)
  e.g. "I gave you the book" → "BOOK I GIVE-YOU"

Usage:
    python -m translation.tier3.train \
        --data path/to/parallel.jsonl \
        --output .translation_cache/checkpoints \
        [--epochs 10] [--lr 3e-4]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator

from translation.config import CACHE_DIR, CHECKPOINTS_DIR, T5_BASE_MODEL, T3_CONFIDENCE_THRESHOLD

# Minimum sentence pairs before Tier 3 is considered viable
MIN_TRAINING_PAIRS = 2_000


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def check_data_sufficiency(data: list[dict]) -> bool:
    """Return True if we have enough data for Tier 3."""
    if len(data) < MIN_TRAINING_PAIRS:
        print(
            f"[tier3] Insufficient training data: {len(data)} pairs "
            f"(minimum {MIN_TRAINING_PAIRS}).\n"
            f"        Ship V1 with Tiers 1+2 only."
        )
        return False
    print(f"[tier3] Training data: {len(data)} pairs ✓")
    return True


def train(
    data_path: Path,
    output_dir: Path = CHECKPOINTS_DIR,
    *,
    epochs: int = 10,
    lr: float = 3e-4,
    batch_size: int = 16,
    eval_split: float = 0.1,
    verbose: bool = True,
) -> Path | None:
    """
    Fine-tune T5-small and save checkpoint. Returns checkpoint path or None
    if data is insufficient.
    """
    try:
        import torch
        from transformers import (
            AutoTokenizer,
            AutoModelForSeq2SeqLM,
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments,
            DataCollatorForSeq2Seq,
        )
        from datasets import Dataset
    except ImportError as e:
        raise ImportError(
            "transformers, torch, and datasets are required for Tier 3 training.\n"
            "Run: pip install transformers torch datasets"
        ) from e

    data = load_jsonl(data_path)
    if not check_data_sufficiency(data):
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    # Split data
    split_idx = int(len(data) * (1 - eval_split))
    train_data = data[:split_idx]
    eval_data = data[split_idx:]

    if verbose:
        print(f"[tier3] Train: {len(train_data)}  Eval: {len(eval_data)}")

    tokenizer = AutoTokenizer.from_pretrained(
        T5_BASE_MODEL, cache_dir=str(CACHE_DIR / "models")
    )

    def preprocess(examples: dict) -> dict:
        # T5 prefix for seq2seq direction
        inputs = ["translate English to ASL: " + e for e in examples["english"]]
        targets = examples["asl"]

        model_inputs = tokenizer(
            inputs, max_length=64, truncation=True, padding="max_length"
        )
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(
                targets, max_length=32, truncation=True, padding="max_length"
            )

        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    train_dataset = Dataset.from_list(train_data).map(preprocess, batched=True)
    eval_dataset = Dataset.from_list(eval_data).map(preprocess, batched=True)

    model = AutoModelForSeq2SeqLM.from_pretrained(
        T5_BASE_MODEL, cache_dir=str(CACHE_DIR / "models")
    )

    args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        warmup_steps=100,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        predict_with_generate=True,
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=collator,
    )

    if verbose:
        print(f"[tier3] Training {T5_BASE_MODEL} for {epochs} epochs…")

    trainer.train()
    trainer.save_model(str(output_dir / "best"))
    tokenizer.save_pretrained(str(output_dir / "best"))

    if verbose:
        print(f"[tier3] Checkpoint saved → {output_dir / 'best'}")

    return output_dir / "best"


def generate(checkpoint_dir: Path, sentences: list[str]) -> list[str]:
    """Run inference on a trained checkpoint (for eval/testing)."""
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
    except ImportError as e:
        raise ImportError("transformers and torch required") from e

    tokenizer = AutoTokenizer.from_pretrained(str(checkpoint_dir))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(checkpoint_dir))
    model.eval()

    inputs_enc = tokenizer(
        ["translate English to ASL: " + s for s in sentences],
        return_tensors="pt",
        max_length=64,
        truncation=True,
        padding=True,
    )

    with torch.no_grad():
        outputs = model.generate(
            **inputs_enc,
            max_length=32,
            num_beams=4,
            early_stopping=True,
        )

    return tokenizer.batch_decode(outputs, skip_special_tokens=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train T5-small for ASL gloss generation")
    parser.add_argument("--data", type=Path, required=True,
                        help="Path to JSONL file with {english, asl} records")
    parser.add_argument("--output", type=Path, default=CHECKPOINTS_DIR)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    result = train(
        args.data,
        args.output,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
    )
    sys.exit(0 if result else 1)
