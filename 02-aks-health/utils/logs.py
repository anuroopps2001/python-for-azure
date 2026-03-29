from kubernetes import client, config
import json

def get_pod_logs(pod_name, namespace):
    config.load_config()

    v1 = client.CoreV1Api()

    try:
        print(f"\n====== Logs for {namespace}/{pod_name} ======")
        # To get the objects stored inside v1
        print(json.dumps(v1))
        pod = v1.list_pod_for_all_namespaces()
        print(json.dumps(pod.to_dict(), indent=2, default=str))
        
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_name=50  # Last 50 lines
        )

        print(logs)

    except Exception as e:
        print(f"Error fetching logs {e}")
