#!/usr/bin/env python3
"""Reproduce the deck's real tokenization, without model inference.

python -m pip install tokenizers==0.22.1
python llm/kubecon-pd-assets/tokenization/reproduce.py [--check]
Downloads only the pinned tokenizer.json to the system temporary directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request
import tokenizers
from tokenizers import Tokenizer

MODEL = 'Qwen/Qwen2.5-7B-Instruct'
REVISION = 'a09a35458c702b33eeacc393d103063234e8bc28'
SHA256 = 'c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539'
URL = f'https://huggingface.co/{MODEL}/resolve/{REVISION}/tokenizer.json'
PROMPT = 'What does Kubernetes do?'
OUTPUT = 'Kubernetes helps teams deploy and scale applications.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare to checked-in manifest')
    args = parser.parse_args()
    assert tokenizers.__version__ == '0.22.1', 'Use the pinned tokenizers==0.22.1'
    artifact = Path(tempfile.gettempdir()) / f'qwen-tokenizer-{REVISION}.json'
    if not artifact.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            artifact.write_bytes(response.read())
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == SHA256
    tokenizer = Tokenizer.from_file(str(artifact))

    def encode(text):
        encoding = tokenizer.encode(text, add_special_tokens=False)
        pieces = [tokenizer.decode([i], skip_special_tokens=False) for i in encoding.ids]
        assert ''.join(pieces) == text
        assert tokenizer.decode(encoding.ids, skip_special_tokens=False) == text
        return {'text': text, 'ids': encoding.ids, 'raw_tokens': encoding.tokens,
                'decoded_pieces': pieces, 'display_pieces': [p.replace(' ', '·') for p in pieces]}

    prompt, output = encode(PROMPT), encode(OUTPUT)
    steps = []
    for i in range(len(output['ids']) - 1):
        steps.append({'step': i+1, 'consumed_position': i+1, 'consumed_id': output['ids'][i],
                      'appended_output_kv_positions': [i+1],
                      'cached_output_positions_after_step': list(range(1, i+2)),
                      'selected_position': i+2, 'selected_id': output['ids'][i+1]})
    manifest = {
        'tokenizer': {'repository': MODEL, 'revision': REVISION, 'asset': 'tokenizer.json',
                      'source_url': URL, 'sha256': SHA256, 'library': 'tokenizers', 'version': tokenizers.__version__},
        'scope': {'raw_tokenizer': True, 'chat_template_applied': False,
                  'add_special_tokens': False, 'model_inference_run': False,
                  'prompt_and_output_encoded_independently': True,
                  'leading_whitespace_added': False,
                  'sentence': 'Illustrative authored completion, not captured model output.',
                  'boundary': 'Continuation uses prompt IDs followed by independently encoded output IDs; concatenated-text retokenization need not preserve this boundary.',
                  'display_legend': '· is one literal ASCII space, not an extra token.'},
        'prompt': prompt, 'output': output,
        'prefill': {'processed_prompt_positions': list(range(1, len(prompt['ids'])+1)),
                    'selected_output_position': 1, 'selected_output_id': output['ids'][0],
                    'cached_output_positions': []},
        'decode_steps': steps,
        'concatenated_text_encoding_for_comparison': encode(PROMPT+OUTPUT),
    }
    path = Path(__file__).with_name('manifest.json')
    if args.check:
        assert json.loads(path.read_text()) == manifest, 'Manifest differs from actual tokenization'
        print('PASS: pinned tokenizer artifact, exact text/IDs/pieces, and cache mapping reproduced')
    else:
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
        print(path)
    for label, result in [('prompt', prompt), ('output', output)]:
        print(label, list(zip(result['ids'], result['display_pieces'])))

if __name__ == '__main__':
    main()
