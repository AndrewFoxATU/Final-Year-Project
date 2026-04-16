# analytics_service/visualisations/run_all.py
# Author: Andrew Fox

# Runs all visualisation scripts in sequence.
# Usage: python -m analytics_service.visualisations.run_all

import importlib

SCRIPTS = [
    "analytics_service.visualisations.plot_data_split",
    "analytics_service.visualisations.plot_training_breakdown",
    "analytics_service.visualisations.plot_label_frequency",
    "analytics_service.visualisations.plot_class_imbalance",
    "analytics_service.visualisations.plot_label_cooccurrence",
    "analytics_service.visualisations.plot_label_f1",
    "analytics_service.visualisations.plot_confusion_matrices",
    "analytics_service.visualisations.plot_feature_importances",
    "analytics_service.visualisations.plot_feature_importance_single",
    "analytics_service.visualisations.plot_decision_tree",
]

if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")  # Save to file without showing windows
    import matplotlib.pyplot as plt
    plt.show = lambda: None  # Suppress show() calls in individual scripts

    for module_path in SCRIPTS:
        name = module_path.split(".")[-1]
        print(f"Running {name}...")
        try:
            mod = importlib.import_module(module_path)
            mod.main()
        except Exception as e:
            print(f"  ERROR in {name}: {e}")

    print("\nAll visualisations complete.")
