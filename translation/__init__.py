"""
SignBridge ASL Translation Engine — Python build-time package.

Produces artifacts consumed by the Android app:
  - translation/patterns.json   (Tier 1: pattern hash table)
  - translation/faiss.index     (Tier 2: FAISS vector index)
  - translation/index_map.json  (Tier 2: vector → ASL gloss mapping)
  - translation/minilm.onnx     (Tier 2: MiniLM-L6 ONNX model)
  - translation/t5_asl.onnx     (Tier 3: T5-small ONNX, if trained)

Run `python -m translation.export` to rebuild all artifacts.
"""
