import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2, aws_iam as iam
from src.bastion_props import BastionProps

from constructs import Construct


class BastionStack(cdk.Stack):
    """
    Bastion host
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        props: BastionProps,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        role = iam.Role(
            self,
            "BastionRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ec2.amazonaws.com"),
                iam.ServicePrincipal("ssm.amazonaws.com"),  # For maintenance service
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                )
            ],
        )
        instance_profile = iam.InstanceProfile(
            self, "BastionInstanceProfile", role=role
        )

        key_pair = ec2.KeyPair.from_key_pair_name(
            self, "BastionKeyPair", props.key_name
        )

        # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/Instance.html
        self.instance = ec2.Instance(
            self,
            "BastionHost",
            instance_type=props.instance_type,
            machine_image=ec2.MachineImage.generic_linux(
                {props.ami_region: props.ami_id}
            ),
            vpc=vpc,
            key_pair=key_pair,
            propagate_tags_to_volume_on_creation=True,
            instance_profile=instance_profile,
            block_devices=props.block_devices,
        )

        cdk.Tags.of(self.instance).add("ManagedInstanceMaintenanceTarget", "yes")
        cdk.Tags.of(self.instance).add("PatchGroup", "prod-default")
