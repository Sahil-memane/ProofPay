# ProofPay Escrow Evidence Fixtures

This directory contains evaluation and verification fixtures for escrow milestone deliverable inspections.

| Filename | Format | Expected Label | Verification Criteria |
| :--- | :--- | :--- | :--- |
| `evidence_complete_spec.pdf` | PDF | **pass** | Valid PDF structure, full specification deliverable, explicit client approval verification. |
| `evidence_signed_agreement.txt` | Text | **pass** | Valid Master Services Agreement with verified digital signatures from both client and freelancer. |
| `evidence_corrupted_scan.pdf` | PDF | **fail** | Corrupted PDF header/trailer, missing xref table, reported as unreadable/broken work product. |
| `evidence_blank_document.txt` | Text | **fail** | Empty placeholder with zero deliverable content or work product attached. |
| `evidence_partial_diff.txt` | Text | **borderline** | Incomplete code patch covering only ~50% of the milestone specification with pending QA review. |
| `evidence_preliminary_mockup.pdf` | PDF | **borderline** | Valid PDF layout but contains preliminary draft mockups missing final client signoff and acceptance. |

## Usage
These fixtures are consumed by automated escrow verification models and human review pipelines to test deliverable validation classifiers.

