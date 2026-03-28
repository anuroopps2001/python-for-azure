from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
import os
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor  # for parallel execution
from azure.mgmt.network import NetworkManagementClient
from collections import Counter  
import time
SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID")

if not SUBSCRIPTION_ID:
    print("Error: SUBSCRIPTION_ID not set")
    sys.exit(1)

# Create a credential (works locally via Azure CLI, in production via managed identity)
credential = DefaultAzureCredential()

# Create management clients to manage the compute resources
compute_client = ComputeManagementClient(credential=credential, subscription_id=SUBSCRIPTION_ID)

# Create network management client to extract the network related details from azure resources
network_client = NetworkManagementClient(credential=credential, subscription_id=SUBSCRIPTION_ID)


# Script usage helper function
def print_usage_examples():
    print("\nExamples:")
    print(" Single VM:")
    print(" python manage.py stop --resource-group my-rg --vm my-vm")
    print(" python manage.py start --resource-group my-rg --vm my-vm")
    print("")
    print(" Tag Based (bulk):")
    print(" python manage.py stop --tag env=dev")
    print(" python manage.py start --tag env=dev")
    print("")
    print(" Dry run")
    print(" python manage.py stop --tag env=dev --dry-run")


# Parse tags(key=vaule)
def parse_tag(tag_str):
    try:
        key, value = tag_str.split("=")
        return key, value
    except ValueError:
        print("The tag must be in format key=value")
        sys.exit(1)
   
def get_resource_group(vm):
    return vm.id.split("/")[4]

# Get VMs current power state
def get_vm_status(resource_group: str, vm_name: str):
    vm = compute_client.virtual_machines.get(
        resource_group_name=resource_group,
        vm_name=vm_name,
        expand="InstanceView"  # InstamceView gets the vm snapshot details
    )

    statuses = vm.instance_view.statuses

    for status in statuses:
        if "PowerState" in status.code:
            return status.code.split("/")[-1]
    
    return "Unknown"

def show_status(vms):
    for vm in vms:
        rg = get_resource_group(vm)
        state = get_vm_status(rg, vm.name)
        
        print(f"{vm.name} -> {state}")

# Get VMs by tags
def get_vms_by_tags(tag_key, tag_value):
    # empty list to store vm details
    vms = []
    for vm in compute_client.virtual_machines.list_all():
        if vm.tags and vm.tags.get(tag_key) == tag_value:
            vms.append(vm)
    return vms


# retry logic
def retry_operation(func, *args, retries=3, delay=3, **kwargs):
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            
            if attempt == retries:
                print("Max retries reached. Giving up..!")
                raise

            time.sleep(delay)

attempt_counter = {"count": 0}

def fake_operation():
    attempt_counter['count'] += 1
    print(f"Running attepmt {attempt_counter['count']}")
    if attempt_counter["count"] < 3:
        raise Exception("Simulation Failed") 
    
    return "Success"

retry_operation(fake_operation)

def stop_operation(resource_group: str, vm_name: str):
    poller = compute_client.virtual_machines.begin_deallocate(
    resource_group_name=resource_group,
    vm_name=vm_name
    )
    return poller.result()
    

def stop_vm(resource_group: str, vm_name: str, dry_run=False):
    """Stop (deallocate) a virtual machine to stop billing."""
    state = get_vm_status(resource_group=resource_group, vm_name=vm_name)
    if state:
        state = state.lower()

    if state and state.split("/")[-1] == "deallocated":
        print(f"{vm_name} → already stopped")
        return "skipped"

    if dry_run:
        print(f"'{vm_name}' -> WILL STOP (dry run)")
        return "skipped"
    try:
       print(f"{vm_name} → stopping (RG: {resource_group})")
       retry_operation(stop_operation,resource_group, vm_name)
       print(f"'{vm_name}' -> stopped")
       return "success"
    
    except Exception as e:
        print(f"{vm_name} → ERROR: {e}")
        return "failed"


def start_operation(resource_group: str, vm_name: str):
    poller = compute_client.virtual_machines.begin_start(
            resource_group_name=resource_group,
            vm_name=vm_name
            )
    return poller.result()

def start_vm(resource_group: str, vm_name: str, dry_run=False):
    """Start a virtual machine"""

    state = get_vm_status(resource_group=resource_group, vm_name=vm_name)

    if state and state.lower().endswith("running"):
        print(f"VM '{vm_name}' is already running. Skipping..!!!")
        ip = get_public_ip(resource_group=resource_group, vm_name=vm_name)
        print(f"Current Public IP is: {ip}")
        return "skipped"
    
    if dry_run:
        print(f"'{vm_name}' -> WILL START (dry run)")
        return "skipped"
    
    try:
        print(f"Starting a VM '{vm_name}' in RG '{resource_group}'..")

        retry_operation(start_operation, resource_group, vm_name)

        ip = get_public_ip(resource_group=resource_group, vm_name=vm_name)
        print(f"'{vm_name}' -> Started and Public is {ip}")
        return "success"
    
    except Exception as e:
        print("Error: You must provide either --vm OR --tag")
        print_usage_examples()
        sys.exit(1)
        return "failed"


# Public IP details of VMs
def get_public_ip(resource_group: str, vm_name: str):
    vm = compute_client.virtual_machines.get(resource_group_name=resource_group, vm_name=vm_name)

    # Get NIC ID
    nic_id = vm.network_profile.network_interfaces[0].id
    nic_name = nic_id.split("/")[-1]  # grab the last object from the list which was created by split

    # Get the nic object
    nic = network_client.network_interfaces.get(resource_group_name=resource_group, network_interface_name=nic_name)
    ip_config = nic.ip_configurations[0]  # Grab the first object


    if ip_config.public_ip_address:
        public_ip_id = ip_config.public_ip_address.id
        public_ip_name = public_ip_id.split("/")[-1]  # Get the actual public nic name present at last object[-1] from the list created by split()
        
        public_ip_obj = network_client.public_ip_addresses.get(resource_group_name=resource_group, public_ip_address_name=public_ip_name)
        return public_ip_obj.ip_address

def list_vms(vms):
    list = []
    for vm in vms:
        rg = get_resource_group(vm)
        list.append(vm.name)
    print(list)


def process_vms(action, vms, dry_run):
    for vm in vms:
        # print("DEBUG VM OBJECT:", vm)
        # print("DEBUG TYPE:", type(vm))
        # print("DEBUG NAME:", vm.name)
        summary = {
            "success" : 0,
            "skipped" : 0,
            "failed"  : 0
        }
        rg = get_resource_group(vm=vm)
      
        if action == "stop":
            result = stop_vm(resource_group=rg, vm_name=vm.name, dry_run=dry_run)
            summary[result] += 1

        elif action == "start":
            result = start_vm(resource_group=rg, vm_name=vm.name, dry_run=dry_run)
            summary[result] += 1
    print("\n===== RESULT SUMMARY =====")
    print(f"✔ Success: {summary['success']}")
    print(f"⚠ Skipped: {summary['skipped']}")
    print(f"✖ Failed: {summary['failed']}")
    print("==========================\n")


def main():
    parser = argparse.ArgumentParser(description="Azure VM Manager - Start/Stop/List VMs")

    parser.add_argument("action", choices=["start", "stop", "list", "status"], help="Action to perform on VMs")


    parser.add_argument("--resource-group", help="Resource group name (required when using --vm)")

    parser.add_argument("--vm", help="Name of the single VM")
    parser.add_argument("--tag", help="Filter VMs by tags (format: key=value)")  # for tag based filtering
    parser.add_argument("--dry-run", action="store_true", help="Show What would happen without executing")

    args = parser.parse_args()

    if not args.vm and not args.tag:  
        print("Error: provide either --vm OR --tag")
        sys.exit(1)

    if args.vm:
        if not args.resource_group:
            print(f"Error: --resource-group is required while using --vm tag")
            sys.exit(1)
        
        vms = [
            compute_client.virtual_machines.get(
                resource_group_name = args.resource_group, 
                vm_name = args.vm
            )
        ]

    else:
        tag_key, tag_value = parse_tag(args.tag)
        vms = get_vms_by_tags(tag_key=tag_key, tag_value=tag_value)

        if not vms:
            print("No VMs found with the given tags")

    

    # Execution summary
    mode = "SINGLE VM" if args.vm  else f"TAG ({args.tag})"
    print("\n==== EXECUTION SUMMARY =====")
    print(f"Action:       : {args.action.upper()}")
    print(f"Mode        : {mode}")
    print(f"Dry Run     : {args.dry_run}")
    print(f"Matched VMs : {len(vms)}")
    print("============================\n")
    
    if args.action == "list":
        list_vms(vms)
    elif args.action == "status":
        show_status(vms)

    else:
        process_vms(action=args.action, vms=vms, dry_run=args.dry_run)
        get_public_ip(resource_group=args.resource_group, vm_name=args.vm)

if __name__ == "__main__":
    main()