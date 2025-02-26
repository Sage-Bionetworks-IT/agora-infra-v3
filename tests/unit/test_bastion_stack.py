import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2, assertions as assertions

from src.network_stack import NetworkStack
from src.bastion_stack import BastionStack
from src.bastion_props import BastionProps


def test_bastion_created():
    cdk_app = cdk.App()
    network_stack = NetworkStack(cdk_app, "NetworkStack", vpc_cidr="10.254.192.0/24")
    key_name = "agora-ci"

    bastion_props = BastionProps(
        key_name=key_name,
        instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
        ami_id="ami-074a6fac5773fe883",
        ami_region="us-east-1",
    )
    bastion_stack = BastionStack(
        scope=cdk_app,
        construct_id="bastion",
        vpc=network_stack.vpc,
        props=bastion_props,
    )

    template = assertions.Template.from_stack(bastion_stack)
    template.has_resource_properties(
        "AWS::EC2::Instance",
        {
            "KeyName": key_name,
            "InstanceType": "t3.micro",
            "Tags": assertions.Match.array_with(
                [
                    {"Key": "ManagedInstanceMaintenanceTarget", "Value": "yes"},
                    {"Key": "PatchGroup", "Value": "prod-default"},
                ]
            ),
        },
    )
