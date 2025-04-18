from os import environ

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2

from src.ecs_stack import EcsStack
from src.helpers.get_package_version import get_alternate_tag_for_edge_package_version
from src.load_balancer_stack import LoadBalancerStack
from src.network_stack import NetworkStack
from src.service_props import ServiceProps, ServiceSecret
from src.service_stack import LoadBalancedServiceStack, ServiceStack
from src.docdb_props import DocdbProps
from src.docdb_stack import DocdbStack
from src.bastion_props import BastionProps
from src.bastion_stack import BastionStack

# get the environment and set environment specific variables
VALID_ENVIRONMENTS = ["dev", "stage", "prod"]
environment = environ.get("ENV")
match environment:
    case "prod":
        environment_variables = {
            "VPC_CIDR": "10.254.174.0/24",
            "FQDN": "newagora-prod.adknowledgeportal.org",
            "CERTIFICATE_ID": "69b3ba97-b382-4648-8f94-a250b77b4994",
            "TAGS": {"CostCenter": "Agora / 112300"},
            "AUTO_SCALE_CAPACITY": {"min": 2, "max": 4},
        }
    case "stage":
        environment_variables = {
            "VPC_CIDR": "10.254.173.0/24",
            "FQDN": "newagora-stage.adknowledgeportal.org",
            "CERTIFICATE_ID": "69b3ba97-b382-4648-8f94-a250b77b4994",
            "TAGS": {"CostCenter": "Agora / 112300"},
            "AUTO_SCALE_CAPACITY": {"min": 2, "max": 4},
        }
    case "dev":
        environment_variables = {
            "VPC_CIDR": "10.254.172.0/24",
            "FQDN": "newagora-dev.adknowledgeportal.org",
            "CERTIFICATE_ID": "e8093404-7db1-4042-90d0-01eb5bde1ffc",
            "TAGS": {"CostCenter": "Agora / 112300"},
            "AUTO_SCALE_CAPACITY": {"min": 1, "max": 2},
        }
    case _:
        valid_envs_str = ",".join(VALID_ENVIRONMENTS)
        raise SystemExit(
            f"Must set environment variable `ENV` to one of {valid_envs_str}. Currently set to {environment}."
        )

stack_name_prefix = f"agora-{environment}"
fully_qualified_domain_name = environment_variables["FQDN"]
environment_tags = environment_variables["TAGS"]
agora_version = "edge"
docdb_master_username = "master"
mongodb_port = 27017
vpn_cidr = "10.1.0.0/16"

# Get image versions
if agora_version == "edge":
    app_version = get_alternate_tag_for_edge_package_version(
        "Sage-Bionetworks", "agora-app"
    )
    api_version = get_alternate_tag_for_edge_package_version(
        "Sage-Bionetworks", "agora-api"
    )
    apex_version = get_alternate_tag_for_edge_package_version(
        "Sage-Bionetworks", "agora-apex"
    )
else:
    app_version = api_version = apex_version = agora_version

print(
    f"Using images: agora-app:{app_version}, agora-api:{api_version}, agora-apex:{apex_version}"
)

# Define stacks
cdk_app = cdk.App()

# recursively apply tags to all stack resources
if environment_tags:
    for key, value in environment_tags.items():
        cdk.Tags.of(cdk_app).add(key, value)

network_stack = NetworkStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-network",
    vpc_cidr=environment_variables["VPC_CIDR"],
)

docdb_props = DocdbProps(
    instance_type=ec2.InstanceType.of(
        ec2.InstanceClass.MEMORY5, ec2.InstanceSize.LARGE
    ),
    master_username=docdb_master_username,
    port=mongodb_port,
)
docdb_stack = DocdbStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-docdb",
    vpc=network_stack.vpc,
    props=docdb_props,
)
docdb_stack.cluster.connections.allow_from(
    ec2.Peer.ipv4(vpn_cidr), ec2.Port.all_traffic(), "Allow all VPN traffic"
)

ecs_stack = EcsStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-ecs",
    vpc=network_stack.vpc,
    namespace=fully_qualified_domain_name,
)

# From AWS docs https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-connect-concepts-deploy.html
# The public discovery and reachability should be created last by AWS CloudFormation, including the frontend
# client service. The services need to be created in this order to prevent an time period when the frontend
# client service is running and available the public, but a backend isn't.
load_balancer_stack = LoadBalancerStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-load-balancer",
    vpc=network_stack.vpc,
)

api_props = ServiceProps(
    container_name="agora-api",
    container_location=f"ghcr.io/sage-bionetworks/agora-api:{api_version}",
    container_port=3333,
    container_memory_reservation=2048,
    container_env_vars={
        "NODE_ENV": "development",
        "MONGODB_PORT": f"{mongodb_port}",
        "MONGODB_NAME": "agora",
        "MONGODB_USER": docdb_master_username,
        "MONGODB_HOST": docdb_stack.cluster.cluster_endpoint.hostname,
    },
    container_secrets=[
        ServiceSecret(
            secret_name=docdb_stack.master_password_secret.secret_name,
            environment_key="MONGODB_PASS",
        )
    ],
    auto_scale_min_capacity=environment_variables["AUTO_SCALE_CAPACITY"]["min"],
    auto_scale_max_capacity=environment_variables["AUTO_SCALE_CAPACITY"]["max"],
)
api_stack = ServiceStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-api",
    vpc=network_stack.vpc,
    cluster=ecs_stack.cluster,
    props=api_props,
)
api_stack.add_dependency(docdb_stack)
api_stack.service.connections.allow_to_default_port(
    docdb_stack.cluster,
    "Allow API container to connect to DocumentDB cluster",
)

app_props = ServiceProps(
    container_name="agora-app",
    container_location=f"ghcr.io/sage-bionetworks/agora-app:{app_version}",
    container_port=4200,
    container_memory_reservation=1024,
    container_env_vars={
        "APP_VERSION": f"{app_version}",
        "CSR_API_URL": f"https://{fully_qualified_domain_name}/api/v1",
        "SSR_API_URL": "http://agora-api:3333/api/v1",
        "TAG_NAME": f"agora/v${app_version}",
        "GOOGLE_TAG_MANAGER_ID": "GTM-WHXXVWKC",
    },
    auto_scale_min_capacity=environment_variables["AUTO_SCALE_CAPACITY"]["min"],
    auto_scale_max_capacity=environment_variables["AUTO_SCALE_CAPACITY"]["max"],
)
app_stack = ServiceStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-app",
    vpc=network_stack.vpc,
    cluster=ecs_stack.cluster,
    props=app_props,
)
app_stack.add_dependency(api_stack)

apex_props = ServiceProps(
    container_name="agora-apex",
    container_location=f"ghcr.io/sage-bionetworks/agora-apex:{apex_version}",
    container_port=80,
    container_memory_reservation=200,
    container_env_vars={
        "API_HOST": "agora-api",
        "API_PORT": "3333",
        "APP_HOST": "agora-app",
        "APP_PORT": "4200",
    },
    auto_scale_min_capacity=environment_variables["AUTO_SCALE_CAPACITY"]["min"],
    auto_scale_max_capacity=environment_variables["AUTO_SCALE_CAPACITY"]["max"],
)
apex_stack = LoadBalancedServiceStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-apex",
    vpc=network_stack.vpc,
    cluster=ecs_stack.cluster,
    props=apex_props,
    load_balancer=load_balancer_stack.alb,
    certificate_id=environment_variables["CERTIFICATE_ID"],
    health_check_path="/health",
)
apex_stack.add_dependency(app_stack)
apex_stack.add_dependency(api_stack)

bastion_props = BastionProps(
    key_name="agora-access",
    instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
    ami_id="ami-074a6fac5773fe883",
    ami_region="us-east-1",
)
bastion_stack = BastionStack(
    scope=cdk_app,
    construct_id=f"{stack_name_prefix}-bastion",
    vpc=network_stack.vpc,
    props=bastion_props,
)
bastion_stack.instance.connections.allow_to(
    docdb_stack.cluster,
    ec2.Port.tcp_range(mongodb_port, 27030),
    "Allow bastion host to connect to DocumentDB cluster",
)
bastion_stack.add_dependency(docdb_stack)

cdk_app.synth()
