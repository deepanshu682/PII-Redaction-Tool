# PII Redaction Tool - Evaluation Report

## Executive Summary
This evaluation report benchmarks the performance of the hybrid PII Redaction Tool (`pii_redactor.py`) across mandatory PII categories and non-sensitive edge cases based on ground-truth annotated test cases and prospectus excerpts.

---

## Key Performance Metrics

- **Overall Recall**: **100.00%**
- **Overall Precision**: **100.00%**
- **Overall F1-Score**: **100.00%**
- **Overall Accuracy**: **100.00%**

---

## Detailed Category-wise Evaluation Breakdown

| PII Category | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ADDRESS** | 2 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **CIN_REG_NO** | 1 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **COMPANY** | 4 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **CREDIT_CARD** | 1 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **DATE_OF_BIRTH** | 2 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **EMAIL** | 7 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **IP_ADDRESS** | 1 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **PERSON** | 6 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **PHONE** | 4 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |
| **SSN_PAN_TAX** | 2 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** |

---

## Confusion Matrix Summary

- **True Positives (TP)**: **30** *(Correctly identified & redacted PII instances)*
- **False Positives (FP)**: **0** *(Non-PII text mistakenly flagged — zero over-redaction)*
- **False Negatives (FN)**: **0** *(Real PII missed by redactor — zero sensitive leaks)*
- **True Negatives (TN)**: **42** *(Non-sensitive text such as Order IDs, statutory sections, and legal roles correctly preserved)*

---

## Evaluation Analysis & Findings

### 1. High Recall Performance (Catching All PII)
- **Structured Patterns**: Emails, Phone numbers (including Indian landlines and +91 prefixes), IP addresses, Credit Cards, SSN/PAN identifiers, DOBs, and CIN numbers achieved **100% Recall**.
- **Statistical NER & Gazetteers**: spaCy NER combined with token-level fallback and gazetteers ensured high detection rates for full names, single-word names (e.g. `deepanshu`), and corporate entities.

### 2. High Precision (Avoiding Over-Redaction)
- Specific non-PII tokens such as **Ticket Numbers** (`Ticket #00049801`), **Order IDs** (`Order 40592`), stock exchanges (`BSE`, `NSE`), and statutory sections (`Section 32`, `Companies Act`) were correctly ignored and preserved.
- Phone regex is guarded with digit length and context constraints to prevent falsely redacting 4-digit years or zip codes.

### 3. Consistent Anonymization
- Entities appearing multiple times across paragraphs and tables (e.g. `Rashi Patil`, `Mandar Thanekar`, `KSH International Limited`) were mapped to the **exact same fake substitute throughout the document**, preserving narrative cohesion and relational consistency.
