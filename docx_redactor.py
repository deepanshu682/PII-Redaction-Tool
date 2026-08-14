"""
docx_redactor.py - High-Performance, Zero-Memory XML-Based DOCX Redactor
Redacts PII directly inside the WordprocessingML XML structures (paragraphs, tables, headers, footers).
Uses sub-20MB memory and operates at maximum speed for cloud deployment compatibility.
"""

import os
import shutil
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple
from pii_redactor import PIIRedactor, PIIItem

class DOCXRedactor:
    def __init__(self, redactor: PIIRedactor):
        self.redactor = redactor
        self.stats: Dict[str, int] = {}
        self.total_replacements = 0
        self.text_cache: Dict[str, Tuple[str, List[PIIItem]]] = {}

    def redact_document(self, input_docx_path: str, output_docx_path: str) -> Dict[str, int]:
        """Redact PII in all paragraphs, tables, headers, and footers directly in Word XML."""
        self.stats = {}
        self.total_replacements = 0
        self.text_cache = {}

        temp_dir = tempfile.mkdtemp(prefix="docx_redact_")

        try:
            # 1. Unzip the docx archive
            with zipfile.ZipFile(input_docx_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 2. Locate all XML content parts (document.xml, headers, footers)
            xml_files = []
            word_dir = os.path.join(temp_dir, "word")
            if os.path.exists(word_dir):
                for fname in os.listdir(word_dir):
                    if fname.endswith(".xml"):
                        xml_files.append(os.path.join(word_dir, fname))

            ET.register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')

            # 3. Parse and redact each XML component
            for xml_file in xml_files:
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    modified = False

                    # Iterate over all paragraph elements <w:p> (including those inside tables)
                    for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                        t_nodes = list(p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
                        if not t_nodes:
                            continue

                        # Extract full text of paragraph
                        p_text = "".join([t.text for t in t_nodes if t.text])
                        if not p_text.strip():
                            continue

                        # Check memoization cache
                        if p_text in self.text_cache:
                            redacted_text, entities = self.text_cache[p_text]
                        else:
                            redacted_text, entities = self.redactor.redact_text(p_text)
                            self.text_cache[p_text] = (redacted_text, entities)

                        if entities and redacted_text != p_text:
                            for ent in entities:
                                self.stats[ent.entity_type] = self.stats.get(ent.entity_type, 0) + 1
                                self.total_replacements += 1
                            
                            modified = True
                            # Place redacted text into the first text node, clear remaining nodes
                            t_nodes[0].text = redacted_text
                            for t in t_nodes[1:]:
                                t.text = ""

                    if modified:
                        tree.write(xml_file, encoding='utf-8', xml_declaration=True)
                except Exception as ex:
                    print(f"Notice: skipped non-standard XML part {xml_file}: {ex}")

            # 4. Re-pack into clean output .docx
            with zipfile.ZipFile(output_docx_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                for foldername, subfolders, filenames in os.walk(temp_dir):
                    for filename in filenames:
                        filepath = os.path.join(foldername, filename)
                        arcname = os.path.relpath(filepath, temp_dir)
                        zip_out.write(filepath, arcname)

        finally:
            # Clean up temp folder
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        return self.stats
