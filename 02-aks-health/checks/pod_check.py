from kubernetes import client, config

def run_pod_checks(namespace=None):
    # Wrapper function to load the kube_config
    config.load_config()

    v1 = client.CoreV1Api()

    if namespace:
        pods = v1.list_namespaced_pod(namespace=namespace)

    else:
        pods = v1.list_pod_for_all_namespaces()
    
    print(f"{pods}")
    print(pods.items)
    issues = []
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
    for pod in pods.items:
        for container in pod.status.container_statuses or []:
            state = container.state

            if state.waiting:
                reason = state.waiting.reason

                if reason in ["CrashLoopBackOff", "ImagePullBackOff"]:
                    issues.append({
                        "type": "CRITICAL",
                        "pod" : pod.metadata.name,
                        "namespace": namespace,
                        "reason" : reason
                    })      
    print_issues(issues)

def print_issues(issues):
    if not issues:
        print("No Critical Issues found..")
        return
    for issue in issues:
        print(f"[{issue['type']}] {issue['namespace']}/{issue['pod']} -> {issue['reason']}")