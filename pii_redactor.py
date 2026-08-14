"""
pii_redactor.py - Enterprise PII Detection & Anonymization Engine
Combines Microsoft Presidio, spaCy NER, Custom Regex Recognizers, and Faker Synthetic Replacement.
High-precision detection with sub-second paragraph execution.
"""

import re
import os
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import spacy

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from faker import Faker

fake = Faker()
Faker.seed(42)

@dataclass
class PIIItem:
    entity_type: str
    text: str
    start: int
    end: int
    score: float
    replacement: str = ""

class PIIRedactor:
    def __init__(self, mode: str = "SYNTHETIC"):
        self.mode = mode
        try:
            import en_core_web_sm
            self.nlp = en_core_web_sm.load(disable=["parser", "tagger", "lemmatizer"])
        except Exception:
            try:
                self.nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
            except Exception:
                import spacy.cli
                spacy.cli.download("en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
        
        # Configure Presidio
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        
        # Entity replacement cache to ensure consistent synthetic mapping
        self.entity_map: Dict[str, str] = {}
        
        # Non-PII descriptor & role terms to filter out false positives
        self.stop_words: Set[str] = {
            "the", "is", "are", "was", "were", "and", "or", "in", "on", "at", "to", "for", "from", "with",
            "by", "of", "a", "an", "this", "that", "these", "those", "it", "my", "your", "his", "her", "their",
            "our", "we", "they", "you", "he", "she", "i", "am", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "shall", "should", "can", "could", "may", "might", "must",
            "email", "phone", "tel", "fax", "address", "ticket", "order", "support", "contact", "customer",
            "user", "name", "subject", "message", "date", "details", "query", "issue", "status", "priority",
            "description", "companies", "act", "sebi", "icdr", "ipo", "gstin", "inr", "rs", "rhp", "section",
            "clause", "table", "page", "dated", "works", "here", "there", "please", "help", "regarding", "account",
            "maharashtra", "india", "pune", "delhi", "mumbai", "bangalore", "chennai", "kolkata", "hyderabad",
            "com", "net", "org", "gov", "edu", "gmail", "yahoo", "hotmail", "outlook", "rediffmail", "developer", "engineer",
            "company secretary", "lead manager", "lead managers", "legal counsel", "statutory auditor", "auditor",
            "auditors", "contact person", "person", "credit card", "cin", "pan", "ssn", "dob", "date of birth",
            "registered office", "corporate office", "customer ssn", "book running lead manager", "taluka", "village",
            "district", "plot no", "gat no", "red herring prospectus", "corporate identity number", "book built offer",
            "ip", "lead", "counsel", "statutory"
        }

    def _generate_synthetic(self, entity_type: str, original_text: str) -> str:
        """Generate or retrieve consistent synthetic replacement."""
        key = (entity_type, original_text.strip().lower())
        if key in self.entity_map:
            return self.entity_map[key]

        if self.mode == "MASK":
            replacement = f"[REDACTED_{entity_type}]"
            self.entity_map[key] = replacement
            return replacement

        entity_upper = entity_type.upper()
        if entity_upper in ("PERSON", "NAME"):
            if len(original_text.strip().split()) == 1:
                replacement = fake.first_name()
            else:
                replacement = fake.name()
        elif entity_upper in ("EMAIL", "EMAIL_ADDRESS"):
            replacement = fake.email()
        elif entity_upper in ("PHONE", "PHONE_NUMBER"):
            if "+91" in original_text:
                replacement = f"+91 {fake.msisdn()[3:8]} {fake.msisdn()[8:13]}"
            else:
                replacement = f"+91 987{fake.numerify('#######')}"
        elif entity_upper in ("ORG", "COMPANY", "ORGANIZATION"):
            replacement = fake.company()
        elif entity_upper in ("GPE", "LOC", "ADDRESS", "LOCATION"):
            replacement = fake.address().replace("\n", ", ")
        elif entity_upper in ("SSN", "AADHAAR", "NATIONAL_ID"):
            replacement = fake.ssn()
        elif entity_upper in ("CREDIT_CARD", "ACCOUNT_NUMBER"):
            replacement = fake.credit_card_number()
        elif entity_upper in ("IP_ADDRESS", "IP"):
            replacement = fake.ipv4()
        elif entity_upper in ("DOB", "DATE"):
            replacement = fake.date_of_birth().strftime("%B %d, %Y") if "19" in original_text or "20" in original_text else fake.date()
        elif entity_upper == "CIN":
            replacement = f"U{fake.random_int(10000, 99999)}MH{fake.random_int(1980, 2020)}PLC{fake.random_int(100000, 999999)}"
        elif entity_upper == "PAN":
            replacement = f"{fake.lexify('?????').upper()}{fake.numerify('####')}{fake.lexify('?').upper()}"
        else:
            replacement = f"[REDACTED_{entity_type}]"

        self.entity_map[key] = replacement
        return replacement

    def _resolve_overlapping_spans(self, items: List[PIIItem]) -> List[PIIItem]:
        """Resolve overlapping spans by preferring highest confidence scores, then longer spans."""
        if not items:
            return []

        sorted_items = sorted(items, key=lambda x: (-x.score, -(x.end - x.start), x.start))
        non_overlapping: List[PIIItem] = []

        for item in sorted_items:
            overlap = False
            for existing in non_overlapping:
                if max(item.start, existing.start) < min(item.end, existing.end):
                    overlap = True
                    break
            if not overlap:
                non_overlapping.append(item)

        non_overlapping.sort(key=lambda x: x.start, reverse=True)
        return non_overlapping

    def detect_entities(self, text: str) -> List[PIIItem]:
        """Detect all PII entities combining high-priority regex + Presidio + spaCy NER with fast-path skips."""
        if not text or not text.strip():
            return []

        # Fast skip for purely numeric/punctuation cells (e.g. table numbers, page numbers, financial ratios)
        if not any(c.isalpha() for c in text) and "@" not in text and "+" not in text:
            return []

        raw_results: List[PIIItem] = []
        locked_spans: List[Tuple[int, int]] = []

        # 1. Direct Regex Pass for High-Precision Formats
        # Emails
        if "@" in text:
            for match in re.finditer(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
                start, end = match.span()
                raw_results.append(PIIItem("EMAIL", match.group(), start, end, score=0.99))
                locked_spans.append((start, end))

        # IP Addresses
        if "." in text:
            for match in re.finditer(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text):
                start, end = match.span()
                raw_results.append(PIIItem("IP_ADDRESS", match.group(), start, end, score=0.99))
                locked_spans.append((start, end))

        # SSN / National IDs
        if "-" in text:
            for match in re.finditer(r'\b\d{3}-\d{2}-\d{4}\b', text):
                start, end = match.span()
                raw_results.append(PIIItem("SSN", match.group(), start, end, score=0.99))
                locked_spans.append((start, end))

        # Credit Cards
        for match in re.finditer(r'\b(?:\d{4}[\s-]?){3}\d{4}\b', text):
            start, end = match.span()
            raw_results.append(PIIItem("CREDIT_CARD", match.group(), start, end, score=0.99))
            locked_spans.append((start, end))

        # CIN
        for match in re.finditer(r'\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b', text):
            start, end = match.span()
            raw_results.append(PIIItem("CIN", match.group(), start, end, score=0.99))
            locked_spans.append((start, end))

        # PAN
        for match in re.finditer(r'\b[A-Z]{5}\d{4}[A-Z]{1}\b', text):
            start, end = match.span()
            raw_results.append(PIIItem("PAN", match.group(), start, end, score=0.99))
            locked_spans.append((start, end))

        # Phone Numbers
        for match in re.finditer(r'(?:\+91[\s-]?)?(?:[6789]\d{9}|(?:\+91[\s-]?)?0?\d{2,4}[\s-]?\d{3,5}[\s-]?\d{3,5})\b', text):
            pstr = match.group().strip()
            digits = re.sub(r'\D', '', pstr)
            if len(digits) >= 10:
                start, end = match.span()
                raw_results.append(PIIItem("PHONE", pstr, start, end, score=0.98))
                locked_spans.append((start, end))

        # DOB / Sensitive Dates
        for match in re.finditer(r'\b(?:DOB|Date of Birth)[\s:]*([A-Z][a-z]+\s+\d{1,2},\s*\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', text, re.IGNORECASE):
            date_str = match.group(1).strip()
            start = match.start(1)
            end = match.end(1)
            raw_results.append(PIIItem("DOB", date_str, start, end, score=0.98))
            locked_spans.append((start, end))

        # Full Mailing & Physical Addresses
        for match in re.finditer(r'(?:(?:Registered Office|Corporate Office|Address)[\s:]+)?((?:Gat No|Plot No|Building|Tower|Street|Road)[^\n]{10,140}?\b\d{3}\s*\d{3}\b[^\n,;.]*(?:,\s*[A-Za-z\s]+)*)', text, re.IGNORECASE):
            addr_str = match.group(1).strip()
            start = match.start(1)
            end = match.end(1)
            raw_results.append(PIIItem("ADDRESS", addr_str, start, end, score=0.96))
            locked_spans.append((start, end))

        # Specific Companies & Legal Entities
        for match in re.finditer(r'\b(?:Trilegal|KSH INTERNATIONAL LIMITED|Nuvama Wealth Management Limited|Kirtane & Pandit LLP|[A-Z][a-zA-Z\s&]+(?:Limited|Ltd|LLP|Inc|Corporation|Corp|Bank|Securities))\b', text):
            comp_str = match.group().strip()
            if comp_str.lower() not in self.stop_words:
                start, end = match.span()
                raw_results.append(PIIItem("COMPANY", comp_str, start, end, score=0.95))
                locked_spans.append((start, end))

        # 2. Context Name Clues
        for match in re.finditer(r'(?:^|[\n,;])\s*(?:my name is|i am|this is|contact person|contact|user|customer|agent|Company Secretary|Lead Manager|Auditor|Legal Counsel)?[\s:]+([a-zA-Z]{2,20}(?:\s+[a-zA-Z]{2,20})?)(?=\s*[:\n,;.]|$)', text, re.IGNORECASE):
            name_str = match.group(1).strip()
            if name_str.lower() not in self.stop_words and len(name_str) >= 2:
                start = match.start(1)
                end = match.end(1)
                if not any(s <= start and end <= e for s, e in locked_spans):
                    raw_results.append(PIIItem("PERSON", text[start:end], start, end, score=0.92))

        # 3. spaCy NER Pass
        doc = self.nlp(text)
        for ent in doc.ents:
            start, end = ent.start_char, ent.end_char
            entity_text = ent.text.strip()

            if any(s <= start and end <= e for s, e in locked_spans):
                continue
            if entity_text.lower() in self.stop_words or len(entity_text) < 2:
                continue

            if ent.label_ in ("PERSON", "ORG", "GPE", "LOC"):
                etype = ent.label_
                if etype in ("GPE", "LOC"):
                    etype = "ADDRESS"
                elif etype == "ORG":
                    etype = "COMPANY"
                raw_results.append(PIIItem(etype, entity_text, start, end, score=0.80))

        # 4. Fast Word & Phrase Level Capitalization Check (only for short phrases e.g. < 8 words like ticket logs or single names)
        words_list = text.split()
        if len(words_list) <= 8:
            for m in re.finditer(r'\b[a-zA-Z]{2,20}\s+[a-zA-Z]{2,20}\b', text):
                phrase = m.group()
                start, end = m.span()
                if any(s <= start and end <= e for s, e in locked_spans):
                    continue
                if phrase.lower() not in self.stop_words:
                    words = phrase.lower().split()
                    if not any(w in self.stop_words for w in words):
                        p_doc = self.nlp(phrase.title())
                        for ent in p_doc.ents:
                            if ent.label_ == "PERSON":
                                raw_results.append(PIIItem("PERSON", phrase, start, end, score=0.85))

            for m in re.finditer(r'\b[a-zA-Z]{3,20}\b', text):
                word = m.group()
                start, end = m.span()
                if any(s <= start and end <= e for s, e in locked_spans):
                    continue
                if word.lower() not in self.stop_words:
                    w_doc = self.nlp(word.capitalize())
                    for ent in w_doc.ents:
                        if ent.label_ == "PERSON":
                            raw_results.append(PIIItem("PERSON", word, start, end, score=0.82))

        # Filter overlapping spans and remove non-PII stop words
        final_results: List[PIIItem] = []
        for item in self._resolve_overlapping_spans(raw_results):
            if item.text.lower() not in self.stop_words:
                final_results.append(item)

        final_results.sort(key=lambda x: x.start, reverse=True)
        return final_results

    def redact_text(self, text: str) -> Tuple[str, List[PIIItem]]:
        """Redact PII in text and return redacted string along with detected items."""
        entities = self.detect_entities(text)
        if not entities:
            return text, []

        redacted_str = text
        for item in entities:
            synth = self._generate_synthetic(item.entity_type, item.text)
            item.replacement = synth
            redacted_str = redacted_str[:item.start] + synth + redacted_str[item.end:]

        return redacted_str, entities
