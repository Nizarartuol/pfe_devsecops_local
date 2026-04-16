"""
CONTROLLER PRINCIPAL — Lance n'importe quel algorithme
Usage : python controller.py --algo threshold
        python controller.py --algo pso
        python controller.py --algo bin_packing --mode FFD
"""
import argparse
import sys
import os

# On ajoute le dossier 'algorithms' au chemin de recherche de Python
current_dir = os.path.dirname(os.path.abspath(__file__))
algorithms_dir = os.path.join(current_dir, "..", "algorithms")
if algorithms_dir not in sys.path:
    sys.path.append(algorithms_dir)


def main():
    parser = argparse.ArgumentParser(description="Custom Autoscaler Controller")
    parser.add_argument("--algo", required=True,
                        choices=["threshold", "least_loaded", "bin_packing",
                                 "predictive", "pso", "genetic", "heuristic"],
                        help="Algorithme à utiliser")
    parser.add_argument("--mode", default="FFD",
                        choices=["FF", "FFD", "BF", "BFD"],
                        help="Mode bin_packing uniquement")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  CUSTOM AUTOSCALER — {args.algo.upper()}")
    print(f"{'='*50}\n")

    if args.algo == "threshold":
        from threshold import run
        run()
    elif args.algo == "least_loaded":
        from least_loaded import run
        run()
    elif args.algo == "bin_packing":
        from bin_packing import run
        run(args.mode)
    elif args.algo == "predictive":
        from predictive import run
        run()
    elif args.algo == "pso":
        from pso import run
        run()
    elif args.algo == "genetic":
        from genetic import run
        run()
    elif args.algo == "heuristic":
        from heuristic import run
        run()

if __name__ == "__main__":
    main()