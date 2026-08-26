# Raw curriculum data (not committed)

## RCAE (required)
curl -L -o data/raw/rcae/china_primary_school_math_knowledge_graph.json \
  https://raw.githubusercontent.com/digitalboy/RCAE_graph_data/main/china_primary_school_math_knowledge_graph.json

## MM-K12 (required)
python scripts/download_raw_data.py --dataset mm_k12

## TAL KG (optional, manual)
Download from https://ai.100tal.com/openData/knowledgeGraph → extract to data/raw/tal_kg/

## TAL-SCQ5K (optional)
python scripts/download_raw_data.py --dataset tal_scq5k
