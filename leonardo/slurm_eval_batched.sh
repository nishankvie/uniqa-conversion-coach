#!/bin/bash
# Batched local-model eval for BOTH bases (Qwen + MiniCPM) on one A100.
# Submit:  sbatch leonardo/slurm_eval_batched.sh
#SBATCH --job-name=persona-eval
#SBATCH --partition=boost_usr_prod
#SBATCH --reservation=s_tra_ncc
#SBATCH --account=euhpc_d30_031
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-task=1
#SBATCH --mem=120GB
#SBATCH --cpus-per-task=8
#SBATCH --time=0:40:00
#SBATCH --output=slurm-eval-%j.out

set -euo pipefail
echo "node=$(hostname) job=$SLURM_JOB_ID"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

cd "$HOME/zero-one"
export PYTHONPATH="$HOME/zero-one:$HOME/zero-one/src"   # root → research/ + leonardo/ ; src → uniqa/
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN="$HOME/.pixi/bin/pixi run --manifest-path $HOME/zero-one/pixi.toml"
N="${N:-100}"; BS="${BS:-48}"

echo "================= QWEN2.5-1.5B ================="
$RUN python3 leonardo/eval_local_batched.py --base "$HOME/models/qwen2.5-1.5b" \
     --adapters leonardo/out --n "$N" --batch_size "$BS" || true

echo "================= MiniCPM5-1B ================="
$RUN python3 leonardo/eval_local_batched.py --base "$HOME/models/minicpm5-1b" \
     --adapters leonardo/out_minicpm --n "$N" --batch_size "$BS" || true

echo "DONE. results: leonardo/out{,_minicpm}/eval_local_batched.json"
