#!/bin/bash
# Leonardo: fine-tune the 3 per-persona LoRA models (sequential on 1x A100).
# Submit:  $LEO put leonardo  &&  $LEO run "sbatch zero-one/leonardo/slurm_finetune.sh"
#SBATCH --job-name=persona-lora
#SBATCH --partition=boost_usr_prod
#SBATCH --reservation=s_tra_ncc
#SBATCH --account=euhpc_d30_031
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-task=1
#SBATCH --mem=120GB
#SBATCH --cpus-per-task=8
#SBATCH --time=2:00:00
#SBATCH --output=slurm-persona-%j.out

set -euo pipefail
echo "node=$(hostname) gpus=${SLURM_GPUS_PER_TASK:-?} job=$SLURM_JOB_ID"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

cd "$HOME/zero-one"
export PYTHONPATH="$HOME/zero-one:$HOME/zero-one/src"   # root → research/+leonardo/ ; src → uniqa/
export HF_HUB_OFFLINE=1                        # compute nodes have no internet; base pre-staged
export TRANSFORMERS_OFFLINE=1
RUN="$HOME/.pixi/bin/pixi run --manifest-path $HOME/zero-one/pixi.toml"   # deps: torch transformers peft trl datasets accelerate
# BASE: pre-stage on a LOGIN node, then point here (compute nodes have NO internet).
#   hf download Qwen/Qwen2.5-1.5B-Instruct --local-dir $HOME/models/qwen2.5-1.5b
#   hf download openbmb/MiniCPM5-1B        --local-dir $HOME/models/minicpm5-1b
# OUTROOT: where adapters land (one root per base model, so runs don't clobber).
#   default Qwen; MiniCPM run:  sbatch --export=ALL,BASE=$HOME/models/minicpm5-1b,OUTROOT=leonardo/out_minicpm slurm_finetune.sh
BASE="${BASE:-$HOME/models/qwen2.5-1.5b}"
OUTROOT="${OUTROOT:-leonardo/out}"
echo "BASE=$BASE  OUTROOT=$OUTROOT"

# data must already be prepared on a login node: python leonardo/prepare_sft.py
for P in judith franz peter; do
  echo "=== fine-tuning persona: $P  (base=$BASE) ==="
  $RUN python3 leonardo/train_persona_lora.py --persona "$P" --base "$BASE" \
       --data leonardo/data --out "$OUTROOT/$P"
done

echo "=== eval: local models vs the frontier dataset stats ==="
$RUN python3 leonardo/eval_local.py --base "$BASE" --adapters "$OUTROOT" --n 100 || true
echo "DONE. Adapters in $OUTROOT/<persona>; eval report printed above."
