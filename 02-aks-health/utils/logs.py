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
        for i in pod.items:
            pod_name = i.metadata.name
            namespace = i.metadata.namespace
            container_name = i.spec.containers[0].name

        print(f"To get logs, use: name={pod_name}, namespace={namespace}, container={container_name}")

        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container = container_name,
            tail_name=50  # Last 50 lines
        )

        print(logs)

    except Exception as e:
        print(f"Error fetching logs {e}")
