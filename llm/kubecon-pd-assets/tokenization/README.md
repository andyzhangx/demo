# Archival Qwen tokenizer example — optional reference only

`manifest.json` and `reproduce.py` are preserved from the previous foundation slides (baseline `93bf4b0e9e8ce88e36ec87f11e7e8f23ab27d348`). **They are not used by the current slides or deck generator.** Their real subword tokens, IDs and cache-step mapping must not be mistaken for the current schematic word-level example.

Current slides 3–4 assume one complete word per token, with punctuation separate, solely to teach prefill/decode. See the [current foundation explanation](../README.md#prefill-and-decode-foundations). No tokenizer library or download is needed to generate the deck.

## What this archive contains

- Raw **Qwen/Qwen2.5-7B-Instruct** tokenizer, Hugging Face `tokenizers==0.22.1`.
- Repository revision: `a09a35458c702b33eeacc393d103063234e8bc28`.
- [Pinned tokenizer.json](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/resolve/a09a35458c702b33eeacc393d103063234e8bc28/tokenizer.json).
- SHA-256: `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539`.
- Independently encoded prompt `What does Kubernetes do?` and authored output `Kubernetes helps teams deploy and scale applications.`, with `add_special_tokens=False`, no chat template or added leading whitespace.
- In this archived example the initial output word splits into `K` + `ubernetes`; the prompt's leading-space Kubernetes is one token. The archive displays a middle dot for a literal space inside a token. These are real tokenizer boundaries but **no model inference was run**.

## Optional reproduction of the archive

Run from the repository root in an environment with the optional tokenizer dependency:

```bash
python -m pip install tokenizers==0.22.1
python llm/kubecon-pd-assets/tokenization/reproduce.py --check
```

The script downloads only the pinned tokenizer artifact to the system temporary directory, validates its SHA-256, encodes the exact strings and checks the archived manifest. No model weights are downloaded. Omitting `--check` rewrites the archived manifest; this does not update the current slides. Keep these files as historical reference, not an input to the word-level teaching diagram.
