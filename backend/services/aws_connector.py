"""AWS Connector Service - executes remediation actions on AWS infrastructure."""
import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _ec2_client():
    return boto3.client("ec2", region_name=AWS_REGION)


def _ssm_client():
    return boto3.client("ssm", region_name=AWS_REGION)


def _autoscaling_client():
    return boto3.client("autoscaling", region_name=AWS_REGION)


def restart_instance(instance_id: str) -> dict:
    """Restart (reboot) an EC2 instance.

    Use when: server is unresponsive, stuck processes, need clean restart.
    """
    if not instance_id:
        return {"success": False, "error": "No instance_id provided"}

    try:
        ec2 = _ec2_client()
        ec2.reboot_instances(InstanceIds=[instance_id])
        return {
            "success": True,
            "action": "restart_instance",
            "instance_id": instance_id,
            "message": f"Instance {instance_id} reboot initiated",
        }
    except Exception as e:
        return {"success": False, "action": "restart_instance", "error": str(e)}


def stop_and_start_instance(instance_id: str) -> dict:
    """Stop and start an EC2 instance (full restart, new host).

    Use when: hardware issues, need fresh underlying host.
    """
    if not instance_id:
        return {"success": False, "error": "No instance_id provided"}

    try:
        ec2 = _ec2_client()
        ec2.stop_instances(InstanceIds=[instance_id])
        waiter = ec2.get_waiter("instance_stopped")
        waiter.wait(InstanceIds=[instance_id], WaiterConfig={"Delay": 10, "MaxAttempts": 30})
        ec2.start_instances(InstanceIds=[instance_id])
        return {
            "success": True,
            "action": "stop_and_start_instance",
            "instance_id": instance_id,
            "message": f"Instance {instance_id} stopped and started (full restart)",
        }
    except Exception as e:
        return {"success": False, "action": "stop_and_start_instance", "error": str(e)}


def run_ssm_command(instance_id: str, commands: list, comment: str = "Runbook remediation") -> dict:
    """Run shell commands on an EC2 instance via SSM (Systems Manager).

    Use when: need to run cleanup, restart services, modify configs on the instance.
    """
    if not instance_id or not commands:
        return {"success": False, "error": "instance_id and commands are required"}

    try:
        ssm = _ssm_client()
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": commands},
            Comment=comment[:100],
            TimeoutSeconds=120,
        )
        command_id = response["Command"]["CommandId"]
        return {
            "success": True,
            "action": "run_ssm_command",
            "instance_id": instance_id,
            "command_id": command_id,
            "commands": commands,
            "message": f"SSM command sent: {comment}",
        }
    except Exception as e:
        return {"success": False, "action": "run_ssm_command", "error": str(e)}


def cleanup_disk(instance_id: str) -> dict:
    """Clean up disk space on an EC2 instance.

    Use when: disk usage is high, file system full alerts.
    Runs common cleanup commands via SSM.
    """
    cleanup_commands = [
        "# Clean up log files older than 7 days",
        "find /var/log -type f -name '*.log' -mtime +7 -delete",
        "find /tmp -type f -mtime +3 -delete",
        "# Clean package cache",
        "yum clean all 2>/dev/null || apt-get clean 2>/dev/null || true",
        "# Remove old journal logs",
        "journalctl --vacuum-time=3d 2>/dev/null || true",
        "# Report new disk usage",
        "df -h /",
    ]
    return run_ssm_command(
        instance_id=instance_id,
        commands=cleanup_commands,
        comment="Runbook: Automated disk cleanup",
    )


def restart_service(instance_id: str, service_name: str) -> dict:
    """Restart a systemd service on an EC2 instance.

    Use when: application service crashed or hung, need to restart without rebooting.
    """
    if not service_name:
        return {"success": False, "error": "No service_name provided"}

    commands = [
        f"systemctl restart {service_name}",
        f"systemctl status {service_name} --no-pager",
    ]
    return run_ssm_command(
        instance_id=instance_id,
        commands=commands,
        comment=f"Runbook: Restart service {service_name}",
    )


def scale_asg(asg_name: str, desired_capacity: int = None, increment: int = 1) -> dict:
    """Scale an Auto Scaling Group up.

    Use when: high CPU/memory across instances, need more capacity.
    """
    if not asg_name:
        return {"success": False, "error": "No asg_name provided"}

    try:
        asg = _autoscaling_client()

        # Get current ASG state
        response = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        if not response["AutoScalingGroups"]:
            return {"success": False, "error": f"ASG '{asg_name}' not found"}

        current = response["AutoScalingGroups"][0]
        current_desired = current["DesiredCapacity"]
        max_size = current["MaxSize"]

        new_desired = desired_capacity if desired_capacity else current_desired + increment
        new_desired = min(new_desired, max_size)  # Don't exceed max

        asg.set_desired_capacity(
            AutoScalingGroupName=asg_name,
            DesiredCapacity=new_desired,
        )
        return {
            "success": True,
            "action": "scale_asg",
            "asg_name": asg_name,
            "previous_capacity": current_desired,
            "new_capacity": new_desired,
            "message": f"ASG '{asg_name}' scaled from {current_desired} to {new_desired}",
        }
    except Exception as e:
        return {"success": False, "action": "scale_asg", "error": str(e)}


def update_config(instance_id: str, config_file: str, find: str, replace: str) -> dict:
    """Update a configuration file on an EC2 instance via SSM.

    Use when: need to change config values (connection strings, timeouts, etc.)
    """
    if not config_file or not find or not replace:
        return {"success": False, "error": "config_file, find, and replace are required"}

    commands = [
        f"cp {config_file} {config_file}.bak",
        f"sed -i 's|{find}|{replace}|g' {config_file}",
        f"echo 'Config updated: {config_file}'",
        f"grep -n '{replace}' {config_file} || echo 'Warning: replacement not found in file'",
    ]
    return run_ssm_command(
        instance_id=instance_id,
        commands=commands,
        comment=f"Runbook: Update config {config_file}",
    )


# ─── Action Router ───

def execute_aws_action(action_type: str, params: dict) -> dict:
    """Route an action to the appropriate AWS connector function.

    Action types:
        - restart_instance: Reboot the EC2 instance
        - restart_service: Restart a specific systemd service
        - cleanup_disk: Run disk cleanup commands
        - scale_up: Increase ASG capacity
        - config_change: Update a config file on the instance
        - run_command: Run arbitrary SSM commands

    Returns the result dict from the executed action.
    """
    instance_id = params.get("instance_id", "")
    
    actions = {
        "restart_instance": lambda: restart_instance(instance_id),
        "restart_service": lambda: restart_service(
            instance_id, params.get("service_name", "login-app")
        ),
        "cleanup_disk": lambda: cleanup_disk(instance_id),
        "scale_up": lambda: scale_asg(
            params.get("asg_name", ""), params.get("desired_capacity")
        ),
        "config_change": lambda: update_config(
            instance_id,
            params.get("config_file", ""),
            params.get("find", ""),
            params.get("replace", ""),
        ),
        "run_command": lambda: run_ssm_command(
            instance_id,
            params.get("commands", []),
            params.get("comment", "Runbook automated command"),
        ),
    }

    handler = actions.get(action_type)
    if not handler:
        return {
            "success": False,
            "error": f"Unknown action_type: {action_type}. Valid: {list(actions.keys())}",
        }

    return handler()
