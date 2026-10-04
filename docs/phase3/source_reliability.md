# Source Reliability and Provenance

## Source Priority Hierarchy

To ensure accuracy and neutrality, CIVICLENS TN does not treat all information sources equally. A strict reliability hierarchy determines the weight of evidence when assessing a political promise.

* **Tier 1: Official Government Sources**
  * E.g., State/Central budget documents, official government portals (`.gov.in`, `.nic.in`), gazette notifications, official scheme guidelines.
* **Tier 2: Official Election/Constitutional/Public Institutions**
  * E.g., Election Commission of India (ECI), Comptroller and Auditor General (CAG) reports, Reserve Bank of India (RBI) publications.
* **Tier 3: Established Public-Interest Organizations and Research Institutions**
  * E.g., Reputable think tanks (PRS Legislative Research), academic publications, recognized non-governmental organizations with verifiable methodologies.
* **Tier 4: Reputable News Organizations**
  * E.g., Major national or regional newspapers and news agencies with established editorial standards. Used primarily for context or tracking announcements.
* **Tier 5: Other Publicly Accessible Sources**
  * E.g., Unofficial aggregators, social media announcements, press releases. Treated with the lowest confidence and usually requiring corroboration from higher tiers.

The system must retain the original source tier for every piece of evidence. Confidence scoring for a promise's status heavily depends on the tier of the supporting evidence.

## Source Provenance Schema

All ingested data must trace back to its exact origin. The reusable source model must capture the following fields where applicable (integrating with or extending the existing `Source`, `DataSource`, and `Document` models):

* **Source ID**: Unique identifier.
* **URL**: Original location of the resource.
* **Source Organization**: Name of the publisher/department.
* **Source Title**: Title of the document or webpage.
* **Source Type**: Classification (e.g., Government Document, News Article).
* **Source Tier**: Tier 1 to Tier 5 categorization.
* **Publication Date**: When the resource was originally published.
* **Collection Timestamp**: When the system retrieved the resource.
* **Document Type**: Format (PDF, HTML, CSV).
* **Financial Year**: Applicable financial year context, if relevant.
* **Content Hash**: SHA-256 (or similar) hash of the downloaded content to verify integrity.
* **HTTP Status**: Response code received during retrieval.
* **Extraction Method**: How the content was parsed (e.g., `pdfplumber`, `beautifulsoup`, `api`).
* **Original Filename**: Name of the file as downloaded.
* **Local Storage Path**: Path where the original file is preserved on disk.
* **License/Usage Notes**: Any copyright or usage restrictions.
* **Retrieval Status**: Success, Failed, Rate Limited, etc.
