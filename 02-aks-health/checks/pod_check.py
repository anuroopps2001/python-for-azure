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
      
