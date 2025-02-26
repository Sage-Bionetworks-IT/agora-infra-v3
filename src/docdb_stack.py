import aws_cdk as cdk
from aws_cdk import (
    aws_docdb as docdb,
    aws_ec2 as ec2,
    aws_secretsmanager as sm,
)
from src.docdb_props import DocdbProps

from constructs import Construct


class DocdbStack(cdk.Stack):
    """
    DocumentDB cluster
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        props: DocdbProps,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.master_password_secret = sm.Secret(
            self,
            "DocDbMasterPassword",
            generate_secret_string=sm.SecretStringGenerator(
                password_length=32, exclude_punctuation=True
            ),
        )

        cluster_parameter_group = docdb.ClusterParameterGroup(
            self,
            "DocDbClusterParameterGroup",
            family="docdb5.0",
            parameters={
                "audit_logs": "disabled",
                "profiler": "enabled",
                "profiler_sampling_rate": "1.0",
                "profiler_threshold_ms": "50",
                "change_stream_log_retention_duration": "10800",
                "tls": "disabled",
                "ttl_monitor": "disabled",
            },
        )

        # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_docdb/DatabaseCluster.html
        self.cluster = docdb.DatabaseCluster(
            self,
            "DocDbCluster",
            master_user=docdb.Login(
                username=props.master_username,
                password=self.master_password_secret.secret_value,
            ),
            instance_type=props.instance_type,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            parameter_group=cluster_parameter_group,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            storage_encrypted=True,
            preferred_maintenance_window="sat:06:54-sat:07:24",
            port=props.port,
            export_profiler_logs_to_cloud_watch=True,
        )
