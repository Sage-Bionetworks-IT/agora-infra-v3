import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2, assertions as assertions

from src.network_stack import NetworkStack
from src.docdb_stack import DocdbStack
from src.docdb_props import DocdbProps


def test_docdb_created():
    cdk_app = cdk.App()
    master_username = "myuser"
    port = 27017
    vpc_cidr = "10.254.192.0/24"
    network_stack = NetworkStack(cdk_app, "NetworkStack", vpc_cidr=vpc_cidr)

    docdb_props = DocdbProps(
        instance_type=ec2.InstanceType.of(
            ec2.InstanceClass.MEMORY5, ec2.InstanceSize.LARGE
        ),
        master_username=master_username,
        port=port,
    )
    docdb_stack = DocdbStack(
        scope=cdk_app,
        construct_id="docdb",
        vpc=network_stack.vpc,
        props=docdb_props,
    )

    template = assertions.Template.from_stack(docdb_stack)
    template.has_resource_properties(
        "AWS::DocDB::DBClusterParameterGroup",
        {
            "Parameters": {
                "audit_logs": "disabled",
                "profiler": "enabled",
                "profiler_sampling_rate": "1.0",
                "profiler_threshold_ms": "50",
                "change_stream_log_retention_duration": "10800",
                "tls": "disabled",
                "ttl_monitor": "disabled",
            }
        },
    )
    template.has_resource_properties(
        "AWS::DocDB::DBCluster",
        {
            "MasterUsername": master_username,
            "MasterUserPassword": assertions.Match.any_value(),
            "DBSubnetGroupName": assertions.Match.any_value(),
            "DBClusterParameterGroupName": assertions.Match.any_value(),
            "StorageEncrypted": True,
            "PreferredMaintenanceWindow": "sat:06:54-sat:07:24",
            "Port": port,
            "EnableCloudwatchLogsExports": ["profiler"],
            "VpcSecurityGroupIds": [
                assertions.Match.any_value(),
            ],
        },
    )
    template.resource_properties_count_is(
        "AWS::EC2::SecurityGroup", assertions.Match.any_value(), 1
    )
