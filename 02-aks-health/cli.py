# CLI handler
import argparse
from checks.pod_check import run_pod_checks  # imporing from checks folder

def run():
    parser = argparse.ArgumentParser(description="AKS Health check")
    parser.add_argument("command", choices=["scan"])
    parser.add_argument("--namespace", default=None)


    args = parser.parse_args()

    if args.command == "scan":
        run_pod_checks(namespace=args.namespace)