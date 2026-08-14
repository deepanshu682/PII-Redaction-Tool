---
title: PII Redaction Tool & Evaluation Suite
emoji: 🔒
colorFrom: indigo
colorTo: cyan
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# PII Redaction Tool & Evaluation Suite

A Python-based solution for automatically detecting, anonymizing, and redacting Personally Identifiable Information (PII) from `.docx` documents and text files while maintaining original document formatting and consistent entity mapping.

---

## Deliverables Included

- **`pii_redactor.py`**: Production engine for scanning document structures, detecting PII (via regex, Presidio, and spaCy NER), and performing layout-preserving pseudonymization.
- **`docx_redactor.py`**: Document-level layout & table structure redactor that processes paragraphs, headers, footers, and complex nested table cells.
- **`evaluate.py`**: Ground-truth evaluation framework that measures Precision, Recall, F1-Score, and Accuracy across all PII categories.
- **`run_redaction.py`**: 1-Click CLI execution pipeline to process documents and display evaluation metrics in terminal.
- **`app.py` & `static/index.html`**: Deployable web application and interactive dashboard featuring a side-by-side Text Workbench, DOCX Drag-and-Drop Redactor, and live Analytics.
- **`Red_Herring_Prospectus_Redacted.docx`**: Redacted output file demonstrating document-wide entity anonymization with over 6,800+ PII replacements.
- **`EVALUATION_REPORT.md`**: Comprehensive quantitative evaluation report detailing benchmark methodology and performance metrics.

---

## Approach Overview

This tool uses a **Hybrid Detection & Consistent Pseudonymization Architecture**:

1. **Deterministic Regex Engine**: Handles structured PII categories with mathematical certainty (Emails, Phone numbers, IP addresses, SSNs/PAN/Tax IDs, Credit Card numbers, Dates of Birth, Corporate Registration/CIN numbers).
2. **Statistical Named Entity Recognition (spaCy NER + Gazetteers)**: Detects unstructured entities such as Full Names (`PERSON`), Corporate/Company names (`ORG`), and Physical Addresses (`ADDRESS`), with support for lowercase and single-word names (e.g. `deepanshu`, `rashi patil`).
3. **Consistent Pseudonymization (Faker)**: Rather than inserting static tags like `[REDACTED]`, real entity names are replaced with realistic fake alternatives (e.g. `Rashi Patil` ➔ `John Doe`, `rashi.patil@gmail.com` ➔ `john.doe@example.com`, `deepanshu` ➔ `Danielle`). An entity mapping cache ensures that every occurrence of an entity throughout the document receives the exact same substitute.
4. **Layout-Preserving DOCX Redactor**: Iterates through paragraphs, runs, and table cells using `python-docx`, ensuring styles, fonts, bolding, and table structures remain intact.

---

## Supported PII Categories

- **Full Names** (`PERSON`)
- **Email Addresses** (`EMAIL`)
- **Phone Numbers** (`PHONE` — Indian +91, STD landlines, 10-digit mobile & International formats)
- **Company / Organization Names** (`COMPANY`)
- **Physical / Mailing Addresses** (`ADDRESS` — including spaced pincodes like `410 501`)
- **SSNs / PAN / Aadhaar / Tax IDs** (`SSN`, `PAN`)
- **Credit Card Numbers** (`CREDIT_CARD`)
- **Dates of Birth** (`DOB`)
- **IP Addresses** (`IP_ADDRESS`)
- **Corporate Identity Numbers** (`CIN`)

---

## Quickstart & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Run PII Redactor CLI
To redact `Red Herring Prospectus.docx` and produce `Red_Herring_Prospectus_Redacted.docx`:
```bash
python run_redaction.py
```

### 3. Run Benchmark Evaluation
To run the quantitative evaluation and verify precision/recall numbers:
```bash
python evaluate.py
```

### 4. Launch Interactive Web Application & Deployment Hub
```bash
python app.py
```
Open your browser at `http://localhost:8000` to access the interactive web UI.

---

## Trade-offs & Analysis

### Trade-offs
- **Pseudonymization vs. Masking**: Pseudonymization preserves text flow and document readability by substituting realistic fake data, but requires maintaining a deterministic mapping dictionary. Masking (e.g., `[REDACTED_NAME]`) is simpler but disrupts reading comprehension. Both modes are selectable in our tool.
- **Speed vs. Contextual Depth**: spaCy's `en_core_web_sm` model combined with priority regex locks provides ultra-fast CPU inference (< 0.05s per paragraph). Larger transformer models (e.g., `en_core_web_trf`) offer marginally higher raw statistical recall on noisy text at the cost of significantly higher memory and latency.

### False Positives & Negatives Handled
- **Phone Numbers vs. Standalone Numbers**: Strict digit boundary rules and context matching prevent non-sensitive numbers (such as `Ticket #00049801`, `Order 40592`, or 4-digit years) from being flagged as phone numbers.
- **Company Names vs. Regulatory Acronyms**: Common statutory and market terms (e.g., `BSE`, `NSE`, `SEBI`, `Section 32`, `Companies Act`, `RHP`, `Lead Manager`) are filtered through an exclusion gazetteer to prevent misclassification as company entities or names.
- **Span Conflict Resolution**: Confidence-based non-maximum suppression prevents nested token overlaps (e.g. ensuring `IP 192.168.1.105` is correctly recognized as an `IP_ADDRESS` rather than split into an organization token).

---

## How to Extend to a New PII Type

To add support for a new PII entity (e.g., **Passport Number**):

1. **Add Pattern Recognizer in `pii_redactor.py`**:
   ```python
   class CustomPassportRecognizer(PatternRecognizer):
       def __init__(self):
           patterns = [Pattern("Passport Pattern", r"\b[A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9]\b", 0.95)]
           super().__init__(supported_entity="PASSPORT", patterns=patterns)
   ```
2. **Register with Analyzer in `PIIRedactor.__init__()`**:
   ```python
   self.analyzer.registry.add_recognizer(CustomPassportRecognizer())
   ```
3. **Add Generator Logic in `_generate_synthetic()`**:
   ```python
   elif entity_upper == "PASSPORT":
       replacement = fake.bothify(text="?#######").upper()
   ```
4. **Add Test Cases in `evaluate.py`**:
   ```python
   {"text": "Passport: A9876543", "ground_truth": [{"entity_type": "PASSPORT", "text": "A9876543"}]}
   ```
