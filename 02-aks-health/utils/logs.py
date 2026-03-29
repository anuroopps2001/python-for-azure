from kubernetes import client, config
import json

def get_pod_logs(pod_name, namespace, target_container=None):
    config.load_config()

    v1 = client.CoreV1Api()

    try:
        print(f"\n====== Logs for {namespace}/{pod_name} ======")
        # Get the details of the pod, user passed 
        pod_info = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        
        # Listing containers inside the pod
        containers_list = []
        for c in pod_info.spec.containers:
            containers_list.append(c.name)
        
        # List container actual status
            for pod in pod_info.items:
                status = pod.status.container_statuses or []
            
                container_name = status.name  # The name (e.g. "azurefile")
    
    # Determine the "Human Readable" status
                if status.state.running:
                    current_state = "Running"
                elif status.state.waiting:
        # This is where 'CrashLoopBackOff' or 'ContainerCreating' lives
                    current_state = f"Waiting ({status.state.waiting.reason})"
                elif status.state.terminated:
                    current_state = f"Terminated (Exit Code: {status.state.terminated.exit_code})"
                else:
                    current_state = "Unknown"

    # Now print both
                print(f"  - {container_name}: {current_state}")

        # If there's only 1 container, and if user don't provide --container, don't bother asking the user
                if not target_container and len(containers_list) == 1:
                    target_container = containers_list[0]

                if not target_container:
            # This handles pods with 2+ containers where the user forgot --container
                    print(f"\n[!] Pod {pod_info.metadata.name} has {len(containers_list)} containers: {', '.join(containers_list)}")
                    print(f"Usage: python cli.py logs --pod {pod_name} --container <name>")
                    return 

                if target_container not in containers_list:
                    print(f"Error: container '{target_container}' not found.")
                    print(f"Available choices: {', '.join(containers_list)}")
                    return

        # 4. EXECUTION: Now that we are 100% sure target_container is valid, fetch logs
                print(f"--- Fetching logs for container: {target_container} ---")
                logs = v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=target_container,
                    tail_lines=50  # Fixed from tail_name to tail_lines
                )
                print(logs if logs else "[No logs found]")

    except Exception as e:
        print(f"Error fetching logs {e}")
