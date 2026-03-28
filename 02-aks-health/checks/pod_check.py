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
            # A Pod has an overall Phase (the high-level status) and individual Container States (the granular details).
            issues.append(create_issue_dict(
                pod, 
                issue_type="PHASE_ISSUE",
                reason=pod.status.phase,
                container_name=container.name,
                suggestion="Check for node pressure or unschedulable taints."
                ))

        # Check individual containers (even if Pod is 'Running', one container might be crashing)
        container_statuses = pod.status.container_statuses or []

        for container in container_statuses:
            # We only care if it's NOT ready
            if not container.ready:
                state = container.state

                severity, suggestion = classify_issues(state) # storing the returned tuple values into separate vars.
                

                # Step 1: Python looks at (state.waiting or state.terminated).
                # Step 2: If waiting is None, it picks terminated.
                # Step 3: Now it has a valid object (the "terminated" object).
                # Step 4: It then calls .reason on that specific object.
                current_reason = (state.waiting or state.terminated).reason
 
                issues.append({
                    "type" : "CRITICAL",
                    "pod" : pod.metadata.name,
                    "namespace" : pod.metadata.namespace,
                    "container" : container.name,
                    "reason" : current_reason,
                    "message" :getattr(state.waiting or state.terminated, 'message', 'N/A'),
                    "suggestion" : suggestion
                })     
    print_issues(issues)

# The '*' means everything after it MUST be called with a name (e.g., issue_type="..", reason="...", container_name="..", message="..")
def create_issue_dict(pod, *, issue_type, reason, container_name="N/A",message="No message", suggestion="No suggestion available"):
    """
    Standardizes the issue dictionary for the health check report.
    """

    return {
        "type" : issue_type, 
        "pod" : pod.metadata.name,
        "namespace" : pod.metadata.namespace,
        "container" : container_name,
        "reason" : reason,
        "message" : message,
        "suggestion": suggestion
    }

def classify_issues(state_obj):
    details = state_obj.waiting or state_obj.terminated
    if not details:
        return "INFO", "No details available"
    
    reason = details.reason
    message = (details.message or "").lower()

    # --- Dynamic Logic for Image Issues ---
    if reason in ["ImagePullBackOff", "ErrImgePull"]:
        for word in ["auth", "denied", "401", "credential"]:
            if word in message:
                return "CRITICAL", "Authentication failed. Check your ACR/Docker pull secrets or 'imagePullSecrets'."  # returns tuple
        
        if any(word in message for word in ["not found", "404", "exist"]):
            return "CRITICAL", "Image or Repository not found. Check for typos in the image name or tag." # returns tuple
        
        return "CRITICAL", "Network or Registry timeout. Check Azure Private Link status." # returns tuple
    
    # --- Dynamic Logic for Crashes ---
    if reason == "CrashLoopBackOff":
        return "CRITICAL", "Application is crashing. Run: kubectl logs <pod> --previous"  # returns tuple
    
    # --- Dynamic Logic for Memory Issues ---
    if reason == "OOMKilled":
        return "CRITICAL", "Memory limit exceeded. Increase resources.limits.memory in YAML."  # returns tuple
    
    # Fallback for anything else
    return "WARNING", f"Unrecognized issue: {reason}. Check describe pod for clues."

def print_issues(issues):
    if not issues:
        print("No Critical Issues found..")
        return
    
    print("\n===== AKS Health Report =====\n")
    for issue in issues:
        print(f"[{issue['type']}] {issue['namespace']}/{issue['pod']}")
        print(f"  → Reason     : {issue['reason']}")
        print(f"  → Suggestion : {issue['suggestion']}\n")