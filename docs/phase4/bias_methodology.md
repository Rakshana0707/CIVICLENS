# Phase 4.7 — Multi-Dimensional News Bias & Coverage Methodology

## Overview

The **CIVICLENS TN News Bias & Political Coverage Analyzer** uses a multi-dimensional statistical framework to analyze political coverage across Tamil and English news publishers.

> [!IMPORTANT]
> The engine strictly avoids single scalar "bias scores" (such as equating sentiment to bias) and does NOT claim to prove intentional political bias. All indicators use neutral statistical terminology such as `coverage difference`, `framing variation`, `topic emphasis divergence`, and `entity prominence`.

---

## Reproducibility & Version Tracking

All indicator calculations are tagged with explicit version metadata:
- **`methodology_version`**: `v1.0`
- **`calculation_version`**: `v1.0`

Every calculated metric is fully reproducible given the underlying raw articles, time windows, and linguistic extraction algorithms.

---

## Multi-Dimensional Indicators (12 Metrics)

### 1. Sentiment Distribution (`sentiment_distribution`)
- **What it measures**: Percentage breakdown of articles categorized as positive ($s > 0.1$), neutral ($-0.1 \le s \le 0.1$), and negative ($s < -0.1$) based on body sentiment scores.
- **What it does NOT measure**: Intentional favoritism or deliberate hostility toward political actors.
- **Limitations**: Automated sentiment lexicons may misinterpret political irony, satire, or complex Tamil rhetorical constructs.

### 2. Headline Sentiment (`headline_sentiment`)
- **What it measures**: Mean and percentage breakdown of sentiment specifically extracted from article headlines.
- **What it does NOT measure**: Editorial intent or full context of the underlying reporting.
- **Limitations**: Headlines often prioritize conciseness or clickability over nuance.

### 3. Article Sentiment (`article_sentiment`)
- **What it measures**: Overall body text sentiment mean and distribution.
- **What it does NOT measure**: The factual accuracy of quotes or official statements contained within the text.

### 4. Entity Prominence (`entity_prominence`)
- **What it measures**: Average prominence score ($0.0$ to $1.0$) of mentioned political persons, parties, and government departments across an outlet's coverage.
- **What it does NOT measure**: Positive or negative stance toward the entity.

### 5. Party / Person Mention Frequency (`entity_mention_frequency`)
- **What it measures**: Raw count and normalized proportion of total mentions for each political entity across articles.
- **What it does NOT measure**: Quality of reporting or editorial approval.

### 6. Topic Emphasis (`topic_emphasis`)
- **What it measures**: Percentage distribution of an outlet's articles across 14 policy topics (e.g., Budget & Economy, Infrastructure, Governance, Education, Law & Order).
- **What it does NOT measure**: Editorial suppression; topic distribution reflects editorial focus and beat allocation.

### 7. Event Coverage Frequency (`event_coverage_frequency`)
- **What it measures**: The ratio of ground-truth legislative/political events covered by an outlet relative to all tracked events.
- **What it does NOT measure**: Proof of intentional suppression or censorship.
- **Interpretation Rule**: Reported as `coverage disparity` or `presence/omission differential`.

### 8. Positive / Negative Framing Distribution (`framing_distribution`)
- **What it measures**: Normalized percentage distribution of positive, negative, and balanced framing across an outlet's reporting.
- **Example**:
  - Source A: Positive Framing = $40.0\%$, Negative Framing = $20.0\%$, Balanced = $40.0\%$
  - Source B: Positive Framing = $15.0\%$, Negative Framing = $45.0\%$, Balanced = $40.0\%$
- **What it does NOT measure**: Proof of intentional partisan agenda.

### 9. Quote Distribution (`quote_distribution`)
- **What it measures**: Average number of direct quotes per article and total quote density.
- **What it does NOT measure**: Accuracy or context of quoted speech.

### 10. Source-Reference Distribution (`sourcing_reference_distribution`)
- **What it measures**: Ratio of official government press releases and department citations relative to general quotes ($\frac{\text{Official Citations}}{\max(1, \text{Quotes} + \text{Citations})}$).
- **What it does NOT measure**: Government compliance or anti-establishment bias.

### 11. Cross-Source Wording Similarity (`wording_similarity`)
- **What it measures**: Pairwise Jaccard text overlap coefficient between two outlets covering shared events.
- **What it does NOT measure**: Plagiarism or wire-service copying without metadata verification.

### 12. Coverage Differences (`coverage_difference`)
- **What it measures**: Quantitative index ($0.0$ to $1.0$) measuring the proportion of unshared events and entity prominence divergence between two outlets.

---

## Statistical Confidence & Sample Size Bounds

To prevent drawing conclusions from noisy data, statistical confidence is computed as follows:

$$\text{Confidence} = \begin{cases} 0.0 & N = 0 \\ \frac{N}{5.0} & 1 \le N < 5 \\ 1.0 & N \ge 5 \end{cases}$$

- **Minimum Sample Size ($N_{\min}$)**: 5 articles per source per time window.
- **Uncertainty Flag**: Any metric with $N < 5$ is flagged with low confidence ($<1.0$).

---

## Interpretation Safeguards

1. **Neutral Terminology Standard**: Use words like `coverage variation`, `framing disparity`, `topic emphasis difference`. Never label outlets as "biased", "fake news", or "corrupt".
2. **Multi-Metric Triangulation**: No single metric should be analyzed in isolation.
3. **Decoupled Entities & Sentiment**: Mentions of a politician or party do not automatically imply endorsement or criticism.
