#!/bin/bash
# Batched eval for ONE base. Submit:
#   sbatch --export=ALL,BASE=$HOME/models/qwen2.5-1.5b,OUTROOT=leonardo/out leonardo/slurm_eval_one.sh
#SBATCH --job-name=persona-eval1
#SBATCH --partition=boost_usr_prod
#SBATCH --reservation=s_tra_ncc
#SBATCH --account=euhpc_d30_031
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-task=1
#SBATCH --mem=120GB
#SBATCH --cpus-per-task=8
#SBATCH --time=0:40:00
#SBATCH --output=slurm-eval1-%j.out

set -euo pipefail
cd "$HOME/zero-one"
export PYTHONPATH="$HOME/zero-one:$HOME/zero-one/src"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN="$HOME/.pixi/bin/pixi run --manifest-path $HOME/zero-one/pixi.toml"
N="${N:-100}"; BS="${BS:-100}"
echo "node=$(hostname) BASE=$BASE OUTROOT=$OUTROOT N=$N"
$RUN python3 leonardo/eval_local_batched.py --base "$BASE" --adapters "$OUTROOT" \
     --n "$N" --batch_size "$BS"
echo "DONE → $OUTROOT/eval_local_batched.json"
