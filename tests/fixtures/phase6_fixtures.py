"""
Phase 6 — Synthetic Test Fixtures for Public Representative Performance Analyzer.

Provides isolated mock public records (Assembly debates HTML, Sansad MP questions JSON,
MPLADS fund release CSVs, Census demographic CSVs, ECI election result PDFs) explicitly
labelled as test fixtures (`is_test_fixture = True`).
"""

from typing import Dict, Any, List

# Explicit Test Fixture Metadata Marker
IS_TEST_FIXTURE = True
FIXTURE_VERSION = "6.0-test"

# 1. Sample TN Legislative Assembly Proceeding (HTML)
MOCK_TNLA_ASSEMBLY_HTML = b"""<!DOCTYPE html>
<html>
<head>
    <title>Tamil Nadu Legislative Assembly Debate - 16th Assembly Session 4</title>
</head>
<body>
    <h1>Tamil Nadu Legislative Assembly Official Proceedings</h1>
    <div class="meta">
        <span class="date">2023-04-12</span>
        <span class="assembly">16th Assembly</span>
    </div>
    <div class="content">
        <h2>Question Hour - Department of School Education</h2>
        <div class="speech">
            <p><strong>Thiru M. K. Stalin (Chief Minister):</strong> The government has allocated new funds for upgrading primary school infrastructure in Kolathur constituency.</p>
        </div>
        <div class="speech">
            <p><strong>Thiru Edappadi K. Palaniswami (Leader of Opposition):</strong> We request details regarding teacher appointments in Salem district schools.</p>
        </div>
    </div>
    <table border="1" class="data-table">
        <thead>
            <tr>
                <th>Constituency</th>
                <th>Member Name</th>
                <th>Question Subject</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Kolathur</td>
                <td>M. K. Stalin</td>
                <td>Smart Classroom Infrastructure</td>
                <td>Answered</td>
            </tr>
            <tr>
                <td>Edappadi</td>
                <td>Edappadi K. Palaniswami</td>
                <td>Rural Drinking Water Supply Scheme</td>
                <td>Answered</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# 2. Sample Parliamentary Question (JSON)
MOCK_SANSAD_QUESTION_JSON = b"""{
  "house": "LOK_SABHA",
  "session": 17,
  "question_number": 1420,
  "question_type": "STARRED",
  "date": "2023-03-15",
  "ministry": "Ministry of Jal Shakti",
  "mp_name": "Kalanidhi Veeraswamy",
  "constituency": "Chennai North",
  "state": "Tamil Nadu",
  "subject": "Desalination Projects and Household Water Supply Coverage",
  "question_text": "Will the Minister of Jal Shakti be pleased to state the total funds sanctioned under Jal Jeevan Mission for Chennai North constituency?",
  "answer_text": "Under Jal Jeevan Mission, Rs. 145 Crore has been allocated for piped water supply expansion in Chennai North district.",
  "is_test_fixture": true
}
"""

# 3. Sample MPLADS Fund Release Statement (CSV)
MOCK_MPLADS_WORK_CSV = b"""work_id,mp_name,constituency,scheme_type,financial_year,sanctioned_amount_inr,expenditure_inr,status,work_category
W-101,Kalanidhi Veeraswamy,Chennai North,MPLADS,FY2022-23,2500000,2450000,COMPLETED,EDUCATION
W-102,Kalanidhi Veeraswamy,Chennai North,MPLADS,FY2022-23,1500000,1480000,COMPLETED,HEALTH
W-103,Dayanidhi Maran,Chennai Central,MPLADS,FY2022-23,3000000,2800000,IN_PROGRESS,ROADS
W-104,Kanimozhi Karunanidhi,Thoothukkudi,MPLADS,FY2022-23,4000000,3950000,COMPLETED,WATER
"""

# 4. Sample Census Demographic Indicators (CSV)
MOCK_CENSUS_DEMOGRAPHIC_CSV = b"""constituency_id,constituency_name,district,total_population,sc_pct,st_pct,literacy_rate_pct,urban_pct
AC-011,Dr. Radhakrishnan Nagar,Chennai,245000,18.5,0.4,89.2,100.0
AC-012,Perambur,Chennai,280000,21.2,0.5,88.4,100.0
AC-013,Kolathur,Chennai,260000,16.8,0.3,91.0,100.0
AC-085,Mettupalayam,Coimbatore,230000,14.2,2.1,84.6,65.4
AC-115,Edappadi,Salem,225000,12.5,0.8,81.3,42.1
"""

# 5. Sample ECI Election Return (PDF Stream)
MOCK_ECI_RESULT_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 215 >>
stream
BT
/F1 12 Tf
72 712 Td
(Election Commission of India - General Election to TNLA 2021) Tj
0 -20 Td
(Constituency: 013 - Kolathur) Tj
0 -20 Td
(Winner: M. K. Stalin (DMK) - Votes: 105,539 (60.86%)) Tj
0 -20 Td
(Runner Up: Aadi Rajaram (AIADMK) - Votes: 35,155 (20.28%)) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000183 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
448
%%EOF
"""

# Discovery Targets & Mock Payload Map for Testing
MOCK_DISCOVERY_TARGETS: List[Dict[str, Any]] = [
    {
        "url": "https://www.assembly.tn.gov.in/proceedings/2023/session4.html",
        "source_id": "SRC-TNLA-PROCEEDINGS",
        "category": "ASSEMBLY_DEBATE",
        "year_or_term": "2023"
    },
    {
        "url": "https://sansad.in/api/questions/ls/2023/1420.json",
        "source_id": "SRC-SANSAD-QUESTIONS",
        "category": "PARLIAMENT_QUESTION",
        "year_or_term": "2023"
    },
    {
        "url": "https://mplads.gov.in/reports/tn/2023/mplads_works.csv",
        "source_id": "SRC-MPLADS-WORKS",
        "category": "MPLADS_WORKS",
        "year_or_term": "FY2022-23"
    },
    {
        "url": "https://censusindia.gov.in/data/tn/demographics_2011.csv",
        "source_id": "SRC-CENSUS-INDIA",
        "category": "CENSUS_DEMOGRAPHICS",
        "year_or_term": "2011"
    },
    {
        "url": "https://results.eci.gov.in/results2021/kolathur_013.pdf",
        "source_id": "SRC-ECI-RESULTS",
        "category": "ELECTION_RETURN",
        "year_or_term": "2021"
    }
]

MOCK_PAYLOAD_MAP: Dict[str, bytes] = {
    "https://www.assembly.tn.gov.in/proceedings/2023/session4.html": MOCK_TNLA_ASSEMBLY_HTML,
    "https://sansad.in/api/questions/ls/2023/1420.json": MOCK_SANSAD_QUESTION_JSON,
    "https://mplads.gov.in/reports/tn/2023/mplads_works.csv": MOCK_MPLADS_WORK_CSV,
    "https://censusindia.gov.in/data/tn/demographics_2011.csv": MOCK_CENSUS_DEMOGRAPHIC_CSV,
    "https://results.eci.gov.in/results2021/kolathur_013.pdf": MOCK_ECI_RESULT_PDF
}
