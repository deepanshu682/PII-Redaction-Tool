"""
evaluate.py - Quantitative Evaluation Benchmark for PII Redaction
Computes Precision, Recall, F1-Score, and Accuracy across all target PII categories.
"""

import json
from typing import List, Dict, Any
from pii_redactor import PIIRedactor, PIIItem

# Comprehensive Ground Truth Benchmark Dataset Covering all 10 PII categories
BENCHMARK_DATASET = [
    {
        "text": "Rashi Patil (rashi.patil@gmail.com, phone: +91 9876543210) requested account update.",
        "ground_truth": [
            {"entity_type": "PERSON", "text": "Rashi Patil"},
            {"entity_type": "EMAIL", "text": "rashi.patil@gmail.com"},
            {"entity_type": "PHONE", "text": "+91 9876543210"}
        ]
    },
    {
        "text": "Rohan Dey (rohan.dey@gmail.com) accessed system from IP 192.168.1.105 for Ticket #00049801.",
        "ground_truth": [
            {"entity_type": "PERSON", "text": "Rohan Dey"},
            {"entity_type": "EMAIL", "text": "rohan.dey@gmail.com"},
            {"entity_type": "IP_ADDRESS", "text": "192.168.1.105"}
        ]
    },
    {
        "text": "KSH INTERNATIONAL LIMITED (CIN: U28129PN1979PLC141032, PAN: AAACK1234F) Registered Office: Gat No. 433, Village Mahalunge, Taluka Khed, District Pune 410 501, Maharashtra, India.",
        "ground_truth": [
            {"entity_type": "COMPANY", "text": "KSH INTERNATIONAL LIMITED"},
            {"entity_type": "CIN", "text": "U28129PN1979PLC141032"},
            {"entity_type": "PAN", "text": "AAACK1234F"},
            {"entity_type": "ADDRESS", "text": "Gat No. 433, Village Mahalunge, Taluka Khed, District Pune 410 501, Maharashtra, India"}
        ]
    },
    {
        "text": "Company Secretary: Mandar Thanekar. Tel: +91 20 6606 4494, Email: cs.connect@kshinternational.com.",
        "ground_truth": [
            {"entity_type": "PERSON", "text": "Mandar Thanekar"},
            {"entity_type": "PHONE", "text": "+91 20 6606 4494"},
            {"entity_type": "EMAIL", "text": "cs.connect@kshinternational.com"}
        ]
    },
    {
        "text": "Lead Manager: Nuvama Wealth Management Limited, Contact Person: Sheetal Parab, Tel: +91 22 6807 7100, Email: sheetal.parab@nuvama.com.",
        "ground_truth": [
            {"entity_type": "COMPANY", "text": "Nuvama Wealth Management Limited"},
            {"entity_type": "PERSON", "text": "Sheetal Parab"},
            {"entity_type": "PHONE", "text": "+91 22 6807 7100"},
            {"entity_type": "EMAIL", "text": "sheetal.parab@nuvama.com"}
        ]
    },
    {
        "text": "Legal Counsel: Trilegal, Email: ipo@trilegal.com. Customer SSN: 123-45-6789, Credit Card: 4532-0154-9821-3304, DOB: October 15, 1985.",
        "ground_truth": [
            {"entity_type": "COMPANY", "text": "Trilegal"},
            {"entity_type": "EMAIL", "text": "ipo@trilegal.com"},
            {"entity_type": "SSN", "text": "123-45-6789"},
            {"entity_type": "CREDIT_CARD", "text": "4532-0154-9821-3304"},
            {"entity_type": "DOB", "text": "October 15, 1985"}
        ]
    },
    {
        "text": "Auditor: Kirtane & Pandit LLP, Contact: Parag Pansare, Email: parag.pansare@kirtanepandit.com.",
        "ground_truth": [
            {"entity_type": "COMPANY", "text": "Kirtane & Pandit LLP"},
            {"entity_type": "PERSON", "text": "Parag Pansare"},
            {"entity_type": "EMAIL", "text": "parag.pansare@kirtanepandit.com"}
        ]
    },
    {
        "text": "deepanshu (email: deepanshu@gmail.com, phone: +91 91586 40360) accessed ticket system.",
        "ground_truth": [
            {"entity_type": "PERSON", "text": "deepanshu"},
            {"entity_type": "EMAIL", "text": "deepanshu@gmail.com"},
            {"entity_type": "PHONE", "text": "+91 91586 40360"}
        ]
    }
]

# Type equivalence mapping
TYPE_ALIASES = {
    "PERSON": {"PERSON", "NAME"},
    "EMAIL": {"EMAIL", "EMAIL_ADDRESS"},
    "PHONE": {"PHONE", "PHONE_NUMBER"},
    "COMPANY": {"COMPANY", "ORG", "ORGANIZATION"},
    "ADDRESS": {"ADDRESS", "GPE", "LOC", "LOCATION"},
    "SSN": {"SSN", "US_SSN", "AADHAAR"},
    "CREDIT_CARD": {"CREDIT_CARD"},
    "DOB": {"DOB", "DATE"},
    "IP_ADDRESS": {"IP_ADDRESS", "IP"},
    "CIN": {"CIN"},
    "PAN": {"PAN"}
}

def is_type_match(gt_type: str, pred_type: str) -> bool:
    aliases = TYPE_ALIASES.get(gt_type, {gt_type})
    return pred_type in aliases or gt_type in TYPE_ALIASES.get(pred_type, {pred_type})

class PIIEvaluator:
    def __init__(self):
        self.redactor = PIIRedactor(mode="SYNTHETIC")

    def run_evaluation(self) -> Dict[str, Any]:
        categories = list(TYPE_ALIASES.keys())
        metrics_per_type = {c: {"TP": 0, "FP": 0, "FN": 0} for c in categories}

        total_gt_count = 0
        total_pred_count = 0

        for sample in BENCHMARK_DATASET:
            text = sample["text"]
            gt_items = sample["ground_truth"]
            total_gt_count += len(gt_items)

            pred_items = self.redactor.detect_entities(text)
            total_pred_count += len(pred_items)

            gt_matched = set()
            pred_matched = set()

            for p_idx, pred in enumerate(pred_items):
                pred_type = pred.entity_type
                std_pred_type = pred_type
                for cat, aliases in TYPE_ALIASES.items():
                    if pred_type in aliases:
                        std_pred_type = cat
                        break

                found = False
                for g_idx, gt in enumerate(gt_items):
                    if g_idx in gt_matched:
                        continue
                    
                    gt_type = gt["entity_type"]
                    text_match = (gt["text"].lower() in pred.text.lower()) or (pred.text.lower() in gt["text"].lower())
                    type_match = is_type_match(gt_type, std_pred_type)

                    if text_match and type_match:
                        metrics_per_type[gt_type]["TP"] += 1
                        gt_matched.add(g_idx)
                        pred_matched.add(p_idx)
                        found = True
                        break

                if not found:
                    if std_pred_type not in metrics_per_type:
                        std_pred_type = "COMPANY"
                    metrics_per_type[std_pred_type]["FP"] += 1

            for g_idx, gt in enumerate(gt_items):
                if g_idx not in gt_matched:
                    gt_type = gt["entity_type"]
                    metrics_per_type[gt_type]["FN"] += 1

        total_tp = sum(m["TP"] for m in metrics_per_type.values())
        total_fp = sum(m["FP"] for m in metrics_per_type.values())
        total_fn = sum(m["FN"] for m in metrics_per_type.values())

        p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        acc = total_tp / (total_tp + total_fp + total_fn) if (total_tp + total_fp + total_fn) > 0 else 0.0

        per_entity_summary = {}
        for c, m in metrics_per_type.items():
            tp, fp, fn = m["TP"], m["FP"], m["FN"]
            cp = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
            cr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            cf1 = (2 * cp * cr) / (cp + cr) if (cp + cr) > 0 else 0.0
            per_entity_summary[c] = {
                "TP": tp, "FP": fp, "FN": fn,
                "Precision": round(cp, 4),
                "Recall": round(cr, 4),
                "F1_Score": round(cf1, 4)
            }

        return {
            "overall": {
                "Total_Ground_Truth": total_gt_count,
                "Total_Predictions": total_pred_count,
                "True_Positives": total_tp,
                "False_Positives": total_fp,
                "False_Negatives": total_fn,
                "Precision": round(p, 4),
                "Recall": round(r, 4),
                "F1_Score": round(f1, 4),
                "Accuracy": round(acc, 4)
            },
            "per_entity_type": per_entity_summary
        }

if __name__ == "__main__":
    evaluator = PIIEvaluator()
    results = evaluator.run_evaluation()
    print("\n================ EVALUATION SUMMARY ================")
    print(json.dumps(results["overall"], indent=2))
    print("\n================ PER-ENTITY METRICS ================")
    print(json.dumps(results["per_entity_type"], indent=2))
