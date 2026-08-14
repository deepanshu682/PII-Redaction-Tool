"""
run_redaction.py - Top-Level CLI Executable for PII Redaction Tool
Generates redacted DOCX file and displays evaluation stats.
"""

import os
import sys
import time
from pii_redactor import PIIRedactor
from docx_redactor import DOCXRedactor
from evaluate import PIIEvaluator

def main():
    print("=" * 70)
    print("           PII REDACTION TOOL - AUTOMATED PIPELINE")
    print("=" * 70)
    
    input_file = "Red Herring Prospectus.docx"
    output_file = "Red_Herring_Prospectus_Redacted.docx"

    if not os.path.exists(input_file):
        print(f"ERROR: Input file '{input_file}' not found in workspace.")
        sys.exit(1)

    print(f"\n[1/3] Initializing Hybrid PII Engine (Presidio + spaCy NER + Faker)...")
    start_time = time.time()
    redactor = PIIRedactor(mode="SYNTHETIC")
    docx_redactor = DOCXRedactor(redactor)

    print(f"\n[2/3] Redacting '{input_file}' -> '{output_file}'...")
    stats = docx_redactor.redact_document(input_file, output_file)
    elapsed = round(time.time() - start_time, 2)

    print(f"\n[+] Redaction completed in {elapsed} seconds.")
    print(f"[+] Output saved to: '{output_file}'")
    print(f"[+] Total PII Replacements: {docx_redactor.total_replacements}\n")

    print("-" * 50)
    print("Entity Category Breakdown:")
    for etype, count in stats.items():
        print(f"  - {etype:<15}: {count} replacements")
    print("-" * 50)

    print("\n[3/3] Running Quantitative Evaluation Benchmark...")
    evaluator = PIIEvaluator()
    eval_results = evaluator.run_evaluation()
    
    overall = eval_results["overall"]
    print("\n" + "=" * 50)
    print("              EVALUATION BENCHMARK SUMMARY")
    print("=" * 50)
    print(f"  Total Ground Truth Entities : {overall['Total_Ground_Truth']}")
    print(f"  Total Model Predictions    : {overall['Total_Predictions']}")
    print(f"  True Positives (TP)        : {overall['True_Positives']}")
    print(f"  False Positives (FP)       : {overall['False_Positives']}")
    print(f"  False Negatives (FN)       : {overall['False_Negatives']}")
    print(f"  Precision                  : {overall['Precision'] * 100:.2f}%")
    print(f"  Recall                     : {overall['Recall'] * 100:.2f}%")
    print(f"  F1-Score                   : {overall['F1_Score'] * 100:.2f}%")
    print(f"  Accuracy                   : {overall['Accuracy'] * 100:.2f}%")
    print("=" * 50)

if __name__ == "__main__":
    main()
