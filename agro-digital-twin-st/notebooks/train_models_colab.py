"""
Colab Training Script for Plant-to-Watershed AI Lab.
Coupling Individual Plant Models with SWAT Hydrology & Climate Projections.

Imports and reuses the core modules from the repository:
  from src.core.dataset_generator import get_dataset
  from src.core.hardware import detect_compute_device
  from src.core.training.trainer import MultiScaleTrainer
  from src.core.inference.bundle import ModelBundle
"""

import os
import sys
import shutil
import zipfile

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.core.dataset_generator import get_dataset
from src.core.hardware import detect_compute_device
from src.core.training.trainer import MultiScaleTrainer
from src.core.inference.bundle import ModelBundle


def main():
    print("=" * 70)
    print("🌽 PLANT-TO-WATERSHED AI LAB — GOOGLE COLAB TRAINING PIPELINE")
    print("=" * 70)

    # 1. Hardware Inspection (GPU/CPU)
    print("\n[1/6] 🔍 Inspecting Hardware Accelerators...")
    hw_info = detect_compute_device()
    print(f"  Device Mode : {hw_info['device_mode']}")
    print(f"  CPU Cores   : {hw_info['cpu']['cores']} ({hw_info['cpu']['model']})")
    print(f"  RAM Total   : {hw_info['ram']['total_gb']} GB")
    print(f"  TensorFlow  : {hw_info['tensorflow']['version']} (GPU Available: {hw_info['tensorflow']['gpu_available']})")

    # 2. Load Multi-Scale Dataset
    print("\n[2/6] 📁 Loading Dataset...")
    df = get_dataset()
    print(f"  Loaded {len(df)} records across {df['watershed_id'].nunique()} watersheds.")
    print(f"  Provenance: {df['data_provenance'].iloc[0]}")

    # 3. Configure Trainer
    target_name = "monthly_runoff_mm"
    learning_mode = "direct"  # or 'residual'
    validation_strategy = "temporal"  # or 'watershed'
    print(f"\n[3/6] ⚙️ Configuring Training Pipeline:")
    print(f"  Target             : {target_name}")
    print(f"  Learning Mode      : {learning_mode}")
    print(f"  Validation Strategy: {validation_strategy}")

    trainer = MultiScaleTrainer(
        target_name=target_name,
        learning_mode=learning_mode,
        validation_strategy=validation_strategy,
        fast_dev_mode=False,
        artifact_base_dir="artifacts"
    )

    # 4. Train Models (3 Traditional + 2 Hybrid)
    print("\n[4/6] 🚀 Training 3 Traditional + 2 Hybrid Models...")
    def print_progress(pct, msg):
        print(f"  [{int(pct * 100)}%] {msg}")

    training_result = trainer.train(df, progress_callback=print_progress)

    # 5. Review Benchmark Results
    print("\n[5/6] 📊 Benchmark & Champion Selection:")
    print(f"  🏆 Champion Model: {training_result['champion_model_name']}")
    for metric_name, val in training_result['champion_metrics'].items():
        print(f"    - {metric_name.upper()}: {val}")

    print("\n  Summary Table of All Models:")
    for model_name, res in training_result["results"].items():
        m = res["metrics"]
        print(f"    * {model_name:32s} | R²: {m.get('r2', 0):.4f} | RMSE: {m.get('rmse', 0):.4f} | NSE: {m.get('nse', 0):.4f}")

    # 6. Bundle & Zip Artifacts for Download
    print("\n[6/6] 📦 Packaging Artifacts for Download...")
    zip_filename = "agro_twin_artifacts.zip"
    artifacts_dir = "artifacts"
    
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(artifacts_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=".")
                zipf.write(file_path, arcname)

    print(f"  ✅ Complete artifact bundle archived to: {zip_filename}")
    print(f"  Ready for deployment in Next.js + FastAPI backend!")


if __name__ == "__main__":
    main()
