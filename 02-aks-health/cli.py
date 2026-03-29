# CLI handler
import argparse
from checks.pod_check import run_pod_checks  # imporing from checks folder
from utils.logs import get_pod_logs
def run():
    parser = argparse.ArgumentParser(description="AKS Health check")
    # 1. Create a "subparser" manager
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 2. Create the 'scan' command branch
    scan_parser = subparsers.add_parser("scan", help="Scan for issues")
    scan_parser.add_argument("--namespace", default=None, help="Namespace to scan for issues")

    # 3. Create the 'logs' command branch
    log_parser = subparsers.add_parser("logs", help="Get pod logs")
    log_parser.add_argument("--namespace", default="default", help="Namespace of the pod")

    # Now --pod is REQUIRED, but ONLY for the 'logs' command
    log_parser.add_argument("--pod", required=True, help="Name of the pod to inspect")

    # Now --container flag if required
    log_parser.add_argument("--container", help="Name of the container to fetch the logs")

    args = parser.parse_args()

    if args.command == "scan":
        print(f"---- Starting AKS Scan in namespace: {args.namespace or 'ALL'} ----")
        run_pod_checks(namespace=args.namespace)
    elif args.command == "logs":
        # The 'logs' command requires --pod, so we know it's safe to use here
        print(f"---- Fetching logs for {args.pod} in  {args.namespace} ----")
        if not args.pod:
            print(f"Error: --pod is required for the logs command")
            return
        get_pod_logs(args.pod, args.namespace, target_container=args.container)