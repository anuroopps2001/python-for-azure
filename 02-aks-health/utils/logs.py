from kubernetes import client, config
import json

def get_pod_logs(pod_name, namespace, target_container=None):
    config.load_config()

    v1 = client.CoreV1Api()

    try:
        print(f"\n====== Logs for {namespace}/{pod_name} ======")
        # Get the details of the pod, user passed 
        pod_info = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        
        containers_list = []
        for c in pod_info.spec.containers:
            containers_list.append(c.name)

        # Scenario A: User didn't specify a container
        if not target_container:
            print(f"\n[!] Pod {pod_info.name} has {len(containers_list)} containers: {', '.join(containers_list) }")
            print(f"Usage: python cli.py logs --pod {pod_name} --container <name>")
            return # Exit early so we don't fetch random logs
        
        # Scenario B: User specified a container that doesn't exist
        if target_container not in containers_list:
            print(f"Error: container {target_container} not found..")
            print(f"Available choices: {', '.join(containers_list)}")

        # Scenario C: Success! Fetch the specific logs
        print(f"--- Fetching logs for container: {target_container} ---")
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container = target_container,
            tail_name=50  # Last 50 lines
        )

        print(logs if logs else ["No logs available"])

    except Exception as e:
        print(f"Error fetching logs {e}")
