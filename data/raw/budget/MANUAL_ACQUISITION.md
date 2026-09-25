# Manual Acquisition of Budget Datasets

Due to geo-blocking or strict TLS/firewall configurations on the Tamil Nadu Government Budget Portal (`http://www.tnbudget.tn.gov.in/` and `https://financedept.tn.gov.in/`), automated scripts encounter persistent connection timeouts. 

To strictly comply with the project constraints (no synthetic data, no third-party substituted data, use only official sources), these files must be downloaded manually by a user via a standard web browser.

## Step-by-Step Instructions

1. **Access the Official Portal:**
   Open a web browser and navigate to `http://www.tnbudget.tn.gov.in/`.

2. **Locate the Detailed Demands for Grants (DDG):**
   * On the portal, navigate to the **"Demands"** or **"Budget Documents"** section.
   * Select the target Financial Year (e.g., `2024-2025`).
   
3. **Download Required Department Files:**
   For Phase 1 analysis, focus on key social and infrastructure sectors. Download the PDFs for:
   * **Demand No. 43:** School Education Department
   * **Demand No. 19:** Health and Family Welfare Department
   *(Additional departments can be added following the same procedure).*

4. **File Placement and Naming (Critical):**
   * Save the downloaded PDF files directly into the `data/raw/budget/` directory within this project.
   * **Do not edit, convert, or clean the files.**
   * Rename the files strictly to match the `filename` expected in `manifest.json`. For example:
     * `Demand_43_School_Education_2024_25.pdf`
     * `Demand_19_Health_and_Family_Welfare_2024_25.pdf`

5. **Update Manifest:**
   If you download additional years (e.g., `2023-24`) or different departments, you must add a new JSON object to the `data/raw/budget/manifest.json` `datasets` array. Ensure you fill out all metadata fields accurately (`source_url`, `source_title`, `financial_year`, etc.).
