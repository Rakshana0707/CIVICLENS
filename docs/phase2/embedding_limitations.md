# Historical Scheme Embedding Limitations

## Overview
As part of Phase 2.12, we utilize `sentence-transformers` (specifically `paraphrase-multilingual-MiniLM-L12-v2`) to generate semantic vector representations of historical scheme text. This enables similarity searches across the Tamil Nadu government corpus.

While powerful, these embeddings are statistical representations of text and **do not possess a perfect or literal understanding of policy nuances, legal criteria, or complex bureaucratic implications.** 

## Language and Model Limitations

### 1. Bilingual Performance and Fallbacks
The model supports over 50 languages, providing robust mapping between English and Tamil concepts. However:
*   **Cultural Context:** The model is trained on global multilingual corpora (e.g., Wikipedia). It may not fully grasp localized Tamil Nadu bureaucratic jargon, acronyms, or specific cultural concepts (e.g., nuances between specific localized caste-based welfare schemes).
*   **Code-switching:** Sentences that rapidly mix English and Tamil within the same phrase may slightly degrade the quality of the embedding representation.

### 2. Semantic Understanding
*   **Superficial Similarity:** The model excels at finding topical overlap (e.g., clustering "education schemes" together). It **does not** accurately differentiate between nuanced policy constraints (e.g., "Scheme A applies to age 18-25" vs "Scheme B applies to age 18-35"). The embeddings might consider these sentences 99% similar despite the critical numerical difference.
*   **Opposite Intents:** Dense vector models sometimes group negations or opposite concepts closely together if they share the same context (e.g., "increases taxes" vs "decreases taxes").

### 3. Length Constraints
*   The `MiniLM` architecture truncates inputs beyond 128/256 tokens depending on configuration. Extremely long scheme descriptions or entire policy note paragraphs will lose semantic weight towards the end of the text. This is why our preprocessing pipeline strictly selects dense fields (Name, Description, Objectives, Beneficiaries) rather than raw document extraction.

### 4. Zero-Shot Capability
These embeddings are generated in a "zero-shot" manner—they have not been fine-tuned on Tamil Nadu government documents specifically. Future phases may require contrastive learning or fine-tuning on a labeled civic dataset to improve accuracy.
