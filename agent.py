from datetime import date, datetime, timedelta
import subprocess
import boto3

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

# LLM
llm = ChatOllama(
    model="gemma4:e2b",
    temperature=0,
    num_ctx=8000
)

# AWS connection
ec2 = boto3.client("ec2", region_name="ap-south-2")
cloudwatch = boto3.client("cloudwatch", region_name="ap-south-2")


# Tools

@tool
def get_date():
    """Get the current date."""
    return str(date.today())


@tool
def get_pods():
    """Get Kubernetes pods."""
    result = subprocess.run(
        ["kubectl", "get", "pods"],
        capture_output=True,
        text=True
    )
    return result.stdout or result.stderr


@tool
def get_ec2_instances():
    """Get AWS EC2 instances and their status."""
    response = ec2.describe_instances()

    instances = []

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instances.append(
                f"ID: {instance['InstanceId']}, "
                f"State: {instance['State']['Name']}"
            )

    return "\n".join(instances) or "No EC2 instances found."


@tool
def get_cpu_usage(instance_id: str):
    """Get EC2 CPU utilization for the last hour."""
    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[
            {"Name": "InstanceId", "Value": instance_id}
        ],
        StartTime=datetime.utcnow() - timedelta(hours=1),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=["Average"]
    )

    data = response["Datapoints"]

    if not data:
        return "No CPU metrics found."

    average = sum(point["Average"] for point in data) / len(data)

    return f"Average CPU utilization: {average:.2f}%"


# LLM + Tools

agent = create_agent(
    model=llm,
    tools=[
        get_date,
        get_pods,
        get_ec2_instances,
        get_cpu_usage
    ],
    system_prompt=(
        "You are a DevOps assistant. "
        "You can check dates, Kubernetes pods, "
        "AWS EC2 instances and CPU utilization."
    )
)

question = input("Ask AI agent: ")

response = agent.invoke({
    "messages": [("user", question)]
})

print(response["messages"][-1].content)