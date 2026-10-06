# CIVICLENS TN — Phase 3.21
## Real Promise Embeddings & Historical Scheme Matching Report

> **IMPORTANT DISCLAIMER: SEMANTIC SIMILARITY ONLY**
> A high similarity score between a political promise and a historical scheme indicates **semantic and topical overlap in text description only**.
> **It does NOT imply policy equivalence, implementation, promise fulfillment, copying, or failure.**
> Similarity matching serves strictly as candidate retrieval to assist analytical research.

---

## 1. Overview & Matching Execution Metrics

- **Execution Timestamp**: `2026-10-06T16:40:36.157523+00:00`
- **Total Valid Promises Embedded**: `1065`
- **Total Phase 2 Historical Schemes**: `20`
- **Matched Promises Count**: `124` (11.6%)
- **Unmatched Promises Count**: `941` (88.4%)
- **Total Candidate Link Pairs Created**: `162`
- **Embedding Vectorizer Model**: `paraphrase-multilingual-MiniLM-L12-v2` (v`1.0.0`)
- **Matching Methodology**: `multilingual_hybrid_cosine_similarity`

---

## 2. Cosine Similarity Score Distribution

Candidate scheme matches are categorized into 4 confidence/quality tiers based on cosine similarity scores:

| Confidence Tier | Score Range | Match Count | Percentage | Description |
| :--- | :---: | :---: | :---: | :--- |
| **High Confidence** | **>= 0.40** | **2** | **1.2%** | Strong topical and domain similarity with historical scheme objectives. |
| **Moderate Confidence** | **0.25 - 0.39** | **23** | **14.2%** | Sectoral or target population overlap with existing schemes. |
| **Low Confidence** | **0.15 - 0.24** | **137** | **84.6%** | Broad category level match; requires researcher verification. |
| **Unmatched** | **< 0.15** | **941** | **88.4%** | Novel policy proposal or no relevant historical scheme in reference dataset. |

---

## 3. Highest Similarity Candidate Matches

Top candidate scheme matches demonstrating high semantic alignment:

| Promise ID | Promise Excerpt | Matched Historical Scheme | Similarity Score |
| :--- | :--- | :--- | :---: |
| `MF-PMK-2016:p11:81f984603a97` | The hut/slum dwellers will be given these concrete houses... | Tamil Nadu Concrete Housing & Slum Rehabilitation Scheme | **0.4090** |
| `MF-AIADMK-2026:p5:74e5b5322e3b` | Free bus travel scheme for men, similar to women: A free bus travel scheme will be implemented for m... | Free Bus Travel Scheme for Women in State Town Buses | **0.3760** |
| `MF-AIADMK-2026:p7:ebb06345f7fa` | Free electricity currently provided to handloom weavers will be increased from 300 units to 450 unit... | Weavers Solar Power Generation Subsidy & Yarn Support Scheme | **0.3558** |
| `MF-AIADMK-2026:p20:65c451c26d56` | Free laptops will be provided at the appropriate time to students studying in government and governm... | Free Laptop Distribution Scheme for High School Students | **0.3568** |
| `MF-AIADMK-2026:p22:55af8cd2287b` | Furthermore, free IVF treatment will be provided in hospitals under the Chief Minister's Comprehensi... | Chief Minister Comprehensive Health Insurance Scheme (CMCHIS) | **0.3659** |
| `MF-AIADMK-2026:p24:d06c16d1f84c` | Muthulakshmi Reddy Maternity Benefit amount will be increased.... | Dr. Muthulakshmi Reddy Maternity Benefit Scheme | **0.3836** |
| `MF-AIADMK-2026:p32:2b480d45f426` | Steps will be taken to implement the Coimbatore and Madurai Metro rail projects.... | Tamil Nadu Metro Rail Expansion Project (Coimbatore & Madurai Phase 1) | **0.4588** |
| `MF-AIADMK-2026:p35:9b11d92014c2` | A separate university for Skill Development will be created for educated youth, and online skill dev... | Naan Mudhalvan Skill Enhancement & Career Guidance Scheme | **0.3601** |

---

## 4. Low Confidence & Borderline Candidate Matches

Candidate matches near the retrieval threshold (0.15 - 0.24) requiring further review:

| Promise ID | Promise Excerpt | Matched Historical Scheme | Similarity Score |
| :--- | :--- | :--- | :---: |
| `MF-PMK-2016:p1:0fbd0757e3ad` | will prescribe fees for students studying in private schools and the fee will be paid by the Govt.... | Free Laptop Distribution Scheme for High School Students | 0.2224 |
| `MF-PMK-2016:p1:0fbd0757e3ad` | will prescribe fees for students studying in private schools and the fee will be paid by the Govt.... | Chief Minister's Primary School Breakfast Scheme | 0.1635 |
| `MF-PMK-2016:p1:0fbd0757e3ad` | will prescribe fees for students studying in private schools and the fee will be paid by the Govt.... | Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn) | 0.1584 |
| `MF-PMK-2016:p1:054273286e48` | schools will be raised and made on a par with Central Govt.... | Free Laptop Distribution Scheme for High School Students | 0.1606 |
| `MF-PMK-2016:p1:a59a3fb60515` | To make school travel hassle free for students, special ‘ STUDENT ONLY BUSSES’ will be introduced... | Free Laptop Distribution Scheme for High School Students | 0.2392 |
| `MF-PMK-2016:p1:a59a3fb60515` | To make school travel hassle free for students, special ‘ STUDENT ONLY BUSSES’ will be introduced... | Chief Minister's Primary School Breakfast Scheme | 0.2009 |
| `MF-PMK-2016:p1:a59a3fb60515` | To make school travel hassle free for students, special ‘ STUDENT ONLY BUSSES’ will be introduced... | Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn) | 0.1654 |
| `MF-PMK-2016:p1:2a8e42b9ffcf` | To enable students crack nationa l level entrance examinations with ease, s pecial coaching classes ... | Free Laptop Distribution Scheme for High School Students | 0.1904 |
| `MF-PMK-2016:p1:2a8e42b9ffcf` | To enable students crack nationa l level entrance examinations with ease, s pecial coaching classes ... | Moovalur Ramamirtham Ammaiyar Higher Education Assurance Scheme (Pudhumai Penn) | 0.1663 |
| `MF-PMK-2016:p1:2a8e42b9ffcf` | To enable students crack nationa l level entrance examinations with ease, s pecial coaching classes ... | Chief Minister's Primary School Breakfast Scheme | 0.1601 |

---

## 5. Unmatched Promises Analysis

Promises with similarity scores below 0.15 represent either **novel policy initiatives** or areas not covered in the reference Phase 2 scheme dataset:

| Promise ID | Promise Excerpt | Domain Category | Status |
| :--- | :--- | :--- | :--- |
| `MF-PMK-2016:p1:d0b3dfcfabd7` | In other words, the present allocation will be doubled... | Uncategorized | Unmatched (<0.15) |
| `MF-PMK-2016:p1:a089a5e10a74` | To ensure the school’s quality standards are maintained, a ‘Director of School Standards’ will be ap... | Education | Unmatched (<0.15) |
| `MF-PMK-2016:p1:d5251b06ff76` | A New Education Policy will be framed incorporating the salient features of the Central Board of Sch... | Education | Unmatched (<0.15) |
| `MF-PMK-2016:p1:266a1de17e04` | This policy will be implemented from the academic year 2017-18... | Uncategorized | Unmatched (<0.15) |
| `MF-PMK-2016:p1:a2247edf8efe` | Each student will be given a ‘tablet’ and through the concept of “e-bag”- an online platform, lesson... | Education | Unmatched (<0.15) |
| `MF-PMK-2016:p1:c72d36e2d49f` | Teachers currently working in Government schools on contractual basis or on a consolidated pay basis... | Education | Unmatched (<0.15) |
| `MF-PMK-2016:p2:2aa27167138a` | Necessary steps will be taken to raise the pay structure for private schools teachers on a par with ... | Education | Unmatched (<0.15) |
| `MF-PMK-2016:p2:56ca5c42f920` | Skill-based e ducation, Knowledge based education and voc ational education will be introduced.... | Education | Unmatched (<0.15) |
| `MF-PMK-2016:p2:b5f970e3abe0` | In this regard, more vocational courses will be added to the exi sting plus one (11 th STD) syllabus... | Uncategorized | Unmatched (<0.15) |
| `MF-PMK-2016:p2:c0dc93c2002b` | The existing ‘Parents -Teachers Associations’ will be converted into ‘School Management Committees’.... | Education | Unmatched (<0.15) |

---

## 6. Analytical Rules & Ethical Boundaries

1. **Candidate Retrieval Only**: Scheme matching provides candidate lists for comparative policy research. It is **not** an automated verdict on implementation status.
2. **Multilingual Vectorization**: Promises in both Tamil and English are mapped onto a shared semantic space to prevent language bias.
3. **Audit Trail**: Every match stored in `promise_scheme_links` includes model metadata, versioning, similarity scores, and mandatory disclaimer text.
