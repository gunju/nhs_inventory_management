from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments


def format_example(example: dict) -> str:
    return (
        f"### Instruction\n{example['instruction']}\n\n"
        f"### Input\n{example['input']}\n\n"
        f"### Output\n{example['output']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()

    dataset = load_dataset("json", data_files=args.dataset)["train"]
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    tokenizer.pad_token = tokenizer.eos_token

    def tokenize(example: dict) -> dict:
        text = format_example(example)
        encoded = tokenizer(text, truncation=True, padding="max_length", max_length=512)
        encoded["labels"] = encoded["input_ids"].copy()
        return encoded

    tokenized = dataset.map(tokenize)
    base_model = AutoModelForCausalLM.from_pretrained(args.base_model)
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(base_model, lora_config)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.output_dir,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=1,
            logging_steps=5,
            save_strategy="epoch",
            learning_rate=2e-4,
            remove_unused_columns=False,
        ),
        train_dataset=tokenized,
    )
    trainer.train()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main()
