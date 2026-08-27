# Pilot curriculum data attribution

ILearn pilot curriculum artifacts under `data/pilot/` (including `knowledge.json`, `example_bank.json`, and derived `data/knowledge_graph.json`) incorporate or reference the following third-party datasets. Each source retains its original license; ILearn usage is limited to curriculum alignment, diagnosis, and example sourcing as documented in `ilearn/data/build_pilot.py`.

---

## RCAE primary-school math knowledge graph

| Field | Value |
| --- | --- |
| **Source** | [digitalboy/RCAE_graph_data](https://github.com/digitalboy/RCAE_graph_data) |
| **File** | `china_primary_school_math_knowledge_graph.json` |
| **License** | [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/) |
| **ILearn use** | Knowledge nodes and prerequisite/related edges for grades 4–6 (`ilearn/data/importers/rcae_graph.py`) |

---

## MM-K12 multimodal math dataset

| Field | Value |
| --- | --- |
| **Source** | [Cierra0506/MM-K12](https://huggingface.co/datasets/Cierra0506/MM-K12) (Hugging Face) |
| **License** | See dataset card on Hugging Face |
| **ILearn use** | Example-bank expansion (`ilearn/data/importers/mm_k12.py`); raw download optional via `scripts/download_raw_data.py --dataset mm_k12` |

> **Note:** MM-K12 raw files are not bundled in this repository. Example expansion from MM-K12 requires a local download to `data/raw/mm_k12/`.

---

## TAL-SCQ5K math competition questions

| Field | Value |
| --- | --- |
| **Source** | [math-eval/TAL-SCQ5K](https://huggingface.co/datasets/math-eval/TAL-SCQ5K) (Hugging Face) |
| **Publisher** | TAL Education Group (好未来) |
| **License** | See dataset card on Hugging Face |
| **ILearn use** | Chinese primary-school example entries and knowledge-point routes (`ilearn/data/importers/tal_scq5k.py`) |

---

## 好未来小学数学知识点标签体系 (TAL knowledge-graph taxonomy)

| Field | Value |
| --- | --- |
| **Source** | [ai.100tal.com open data — knowledge graph](https://ai.100tal.com/openData/knowledgeGraph) |
| **Publisher** | TAL Education Group (好未来) |
| **ILearn use** | Reference taxonomy for knowledge-point aliasing and future KG enrichment (`data/raw/tal_kg/`; manual download) |

---

## MV-MATH multimodal math benchmark

| Field | Value |
| --- | --- |
| **Paper** | Wang, Peijie et al. *MV-MATH: Evaluating Multimodal Math Reasoning in Multi-Visual Contexts.* CVPR 2025, pp. 19541–19551. [Open Access](https://openaccess.thecvf.com/content/CVPR2025/html/Wang_MV-MATH_Evaluating_Multimodal_Math_Reasoning_in_Multi-Visual_Contexts_CVPR_2025_paper.html) |
| **Dataset** | [PeijieWang/MV-MATH](https://huggingface.co/datasets/PeijieWang/MV-MATH) (Hugging Face) |
| **License** | See dataset card on Hugging Face |
| **ILearn use** | Curriculum-bound multimodal assessment bank (`ilearn/data/importers/mv_math.py`, `data/pilot/multimodal_bank.json`); raw download via `scripts/download_raw_data.py --dataset mv_math --download` |

> **Note:** MV-MATH raw files and committed pilot images under `data/pilot/assets/mv_math/` are not bundled in full. Import requires a local download to `data/raw/mv_math/`.

---

## Rebuild

To regenerate pilot artifacts from raw sources:

```bash
python -m ilearn.data.build_pilot
```

See `data/raw/README.md` and `scripts/download_raw_data.py` for download instructions.
