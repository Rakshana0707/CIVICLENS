# Historical Scheme Theme Analysis Limitations

## Overview
Phase 2.17 introduces unsupervised theme clustering using Semantic Embeddings and K-Means clustering, accompanied by TF-IDF keyword extraction. This module automatically groups structurally similar historical schemes into configurable "themes".

## Core Methodological Limitations

### 1. Absence of Political Intent
The clustering algorithm relies entirely on vector distances in a high-dimensional semantic space. **It is a purely mathematical construct.** 
* It carries no ability to detect political alignment, historical bias, or governmental intent.
* A cluster simply means the texts utilize similar vocabulary (e.g., words like "agriculture," "subsidy," "farmer"), rather than suggesting the schemes serve identical political goals. 
* Care must be taken not to assign subjective labels or infer undocumented motivations based on automatically grouped themes.

### 2. Semantic vs. Functional Similarity
The K-Means algorithm operates on the textual descriptions of the schemes. 
* Two schemes that conceptually address "water management" will be grouped together, even if one is a punitive regulatory framework and the other is a financial subsidy program.
* Do not assume that schemes within the same theme utilize the same legal or functional mechanics.

### 3. K-Means Rigidity (n_clusters)
The number of clusters ($K$) is defined manually by the user.
* Forcing a rigid number of clusters often splinters large, natural topics into arbitrary sub-topics or falsely merges distinct outliers into unrelated groups just to satisfy the math.
* The algorithm forces every scheme into a cluster; there is no "noise" classification (unlike DBSCAN). Outlier schemes will invariably distort the theme they are forcibly assigned to.

### 4. TF-IDF Keyword Extraction Bias
We utilize Term Frequency-Inverse Document Frequency (TF-IDF) solely to extract interpretable labels for the dense vector clusters. 
* Because we filter standard English stopwords, the generated keywords heavily skew toward specific nouns. 
* If a cluster contains highly diverse terminology across Tamil and English, the TF-IDF representation may return generic artifact words that scored high merely due to rare repetition.

### 5. Multilingual Dilution
While the underlying embeddings natively map Tamil and English to the same space, the TF-IDF keyword extractor is primarily configured for standard tokenization. Tamil morphological roots (which frequently agglutinate) may split unpredictably, leading to less readable keywords for clusters heavily reliant on Tamil descriptions.
