# CISO Assistant Community — ISO Standard Library Files

## Source

These files were downloaded from the open-source project **[CISO Assistant Community](https://github.com/intuitem/ciso-assistant-community)**, maintained by [intuitem](https://www.intuitem.com/). CISO Assistant is a GRC (Governance, Risk & Compliance) platform that provides structured, machine-readable representations of international security and management standards. The libraries are distributed under an open license and are packaged by intuitem for direct import into the CISO Assistant platform.

> **Note:** These files contain only the *outline* of each standard (clause structure, control identifiers, and descriptive summaries). They are not a substitute for the full official standards, which must be purchased from [ISO](https://www.iso.org).

---

## Files in This Directory

### `iso27001-2022.yaml.txt`

The most current version of the ISO/IEC 27001 standard (**2022 edition**).

- **Full title:** Information security, cybersecurity and privacy protection — Information security management systems — Requirements
- **URN:** `urn:intuitem:risk:library:iso27001-2022`
- **Size:** ~10,700 lines
- **Contents:**
  - **Clauses 4–10** — the normative ISMS requirements (Context, Leadership, Planning, Support, Operation, Performance Evaluation, Improvement)
  - **Annex A** — 93 reference controls organized into 4 categories (A.5 Organizational, A.6 People, A.7 Physical, A.8 Technological), with ~190 individual control entries
  - Full multi-language translations (EN, FR, ES, DE, CS, SV, ZH)
- **Key differences from 2013:** Restructured Annex A with fewer but broader controls; introduces themes and attributes for each control; reflects modern cloud, DevOps, and threat-intelligence practices.

---

### `iso27001-2013.yaml.txt`

The previous version of ISO/IEC 27001 (**2013 edition**), still relevant for organizations under legacy certification or running gap assessments between editions.

- **Full title:** Information security, cybersecurity and privacy protection — Information security management systems — Requirements
- **URN:** `urn:intuitem:risk:library:iso27001-2013`
- **Size:** ~1,330 lines
- **Contents:**
  - **Clauses 4–10** — normative ISMS requirements
  - **Annex A** — 114 controls across 14 domains (A.5–A.18)
- **Use case:** Useful for mapping legacy controls or performing gap analysis between the 2013 and 2022 editions.

---

### `iso22301-2019.yaml.txt`

The Business Continuity Management Systems standard.

- **Full title:** ISO 22301:2019 — Security and resilience — Business continuity management systems — Requirements outline
- **URN:** `urn:intuitem:risk:library:iso22301-2019`
- **Size:** ~530 lines
- **Contents:**
  - **Clauses 4–10** — normative BCMS requirements
  - Maturity scoring model: 5-level scale from *Incomplete (0)* to *Optimizing (5)*
- **Relevance to this project:** ISO 27001 Annex A controls (particularly A.5.29–A.5.30 on business continuity) reference ISO 22301 directly. Including this file allows cross-standard traceability in assessments.

---

### `iso42001-2023.yaml.txt`

The Artificial Intelligence Management Systems standard — the most recent addition to the ISO management system family.

- **Full title:** ISO 42001:2023 — Artificial intelligence — Requirements and Controls outline
- **URN:** `urn:intuitem:risk:library:iso42001-2023`
- **Size:** ~800 lines
- **Contents:**
  - **Clauses 4–10** — normative AI management system requirements
  - **Annex A** — AI-specific reference controls
  - Maturity scoring model: 5-level scale from *Incomplete (0)* to *Optimizing (5)*
- **Relevance to this project:** Since our multi-agent system is built on AI/GenAI foundations models, ISO 42001 provides the governance layer for responsible AI use within the ISMS scope. It also supports clients seeking to demonstrate AI risk management as part of their ISO 27001 certification.

---

## File Format

All files use a `.yaml.txt` extension (YAML content with a `.txt` suffix, as GitHub renders them in plain text). Each file follows the **CISO Assistant Library v2 schema**, structured as:

```yaml
urn:              # Unique resource name for the library
locale:           # Primary language (en)
ref_id:           # Official standard identifier
name:             # Human-readable name
description:      # Brief description
provider:         # Issuing body (ISO/IEC or ISO)
packager:         # intuitem
version:          # Library version number
publication_date: # Date of last library update

objects:
  reference_controls:   # Annex A / appendix controls (where applicable)
    - urn:
      ref_id:           # e.g. A.5.1
      name:
      description:
      translations: {}

  framework:            # Clause-level requirement structure
    requirement_nodes:
      - urn:
        ref_id:         # e.g. '4', '4.1'
        depth:          # Nesting level
        parent_urn:
        name:
        description:
        assessable:     # Whether this node can be assessed (true/false)
```

---

## How to Use These Files in This Project

### 1. Direct Reference for Agent Knowledge

The YAML files serve as structured knowledge for the multi-agent system. Each agent responsible for a specific ISO domain (e.g., the Risk Assessment agent, the Audit Planning agent) can load the relevant clauses and controls as its baseline reference, mapping client evidence to specific `ref_id` entries.

### 2. Gap Assessment Mapping

Use `iso27001-2013.yaml.txt` alongside `iso27001-2022.yaml.txt` to generate automated gap analysis reports for clients transitioning from the 2013 to the 2022 edition. The `ref_id` fields provide a stable key for cross-mapping.

### 3. Cross-Standard Traceability

The four standards together cover an integrated compliance scope:

| Standard | Scope | Role in Project |
|---|---|---|
| ISO 27001:2022 | Information security management | Primary certification target |
| ISO 27001:2013 | Information security management (legacy) | Gap analysis baseline |
| ISO 22301:2019 | Business continuity management | Supporting control domain |
| ISO 42001:2023 | AI management systems | AI/GenAI governance layer |

### 4. Importing into CISO Assistant

If the project uses a self-hosted or SaaS instance of CISO Assistant, these files can be imported directly via the platform's library import feature. Rename the `.yaml.txt` files back to `.yaml` before importing.

### 5. Scoring and Maturity

The ISO 22301 and ISO 42001 files include a 0–5 maturity scoring model (`min_score`, `max_score`, `scores_definition`). These can be used to build assessment rubrics for evaluating how mature a client organization is against each control domain.

---

## Related Directories

- `../iso27001/` — Additional ISO 27001 reference materials (templates, guides)
- `../audit-methodology/` — Audit process documentation used alongside these standards
- `../audit-examples/` — Sample completed assessments

---

## License & Attribution

These library files are provided by [intuitem](https://www.intuitem.com/) via the [ciso-assistant-community](https://github.com/intuitem/ciso-assistant-community) repository. The standard outlines are summaries; the full normative texts are copyright of ISO and must be licensed separately from [iso.org](https://www.iso.org).
