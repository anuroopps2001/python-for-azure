from kubernetes import client, config
from kubernetes.client import V1PodList, V1Pod
import json

def run_pod_checks(namespace=None):
    # Wrapper function to load the kube_config
    config.load_config()

    v1 = client.CoreV1Api()

    if namespace:
        pods = v1.list_namespaced_pod(namespace=namespace)

    else:
        pods = v1.list_pod_for_all_namespaces()
    
    # for knowing the properties of pods object
    # print(json.dumps(pod.to_dict(), indent=2, default=str))  

# The object returned (V1PodList)
# {
#     'api_version': 'v1',
#     'kind': 'PodList',
#     'metadata': {...},
#     'items': [  # <--- This is the actual list of V1Pod objects
#         V1Pod, 
#         V1Pod, 
#         ...
#     ]
# }

    issues = []
    
    for pod in pods.items:
        
        # Check if the overall Pod phase is not 'Running' or 'Succeeded'
        if pod.status.phase not in ["Running", "Succeeded"]:
            issues.append(create_issue_dict(pod, "PHASE_ISSUE", pod.status.phase))

        # Check individual containers (even if Pod is 'Running', one container might be crashing)
        container_statuses = pod.status.container_statuses or []
        for container in container_statuses:
            if not container.ready:
                state = container.state

                if state.waiting:
                    reason = state.waiting.reason
                    msg = state.waiting.message

                elif state.terminated:
                    reason = state.terminated.reason or f"ExitCode:{state.terminated.exit_code}"
                    msg = state.terminated.message
                else:
                    reason = 'unknown'
                    msg = "Container is not ready but has no specific waiting/terminated state"

                issues.append({
                    "type" : "CRITICAL",
                    "pod" : pod.metadata.name,
                    "namespace" : pod.metadata.namespace,
                    "container" : container.name,
                    "reason" : reason,
                    "message" : msg
                })     
    print_issues(issues)

def print_issues(issues):
    if not issues:
        print("No Critical Issues found..")
        return
    for issue in issues:
        print(f"[{issue['type']}] {issue['namespace']}/{issue['pod']} -> {issue['reason']}")