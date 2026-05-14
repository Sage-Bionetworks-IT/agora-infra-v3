from aws_cdk import aws_ec2 as ec2


class DocdbProps:
    """
    DocumentDB properties

    instance_type: What type of instance to start for the replicas
    master_username: The database admin account username
    port: The MongoDB port
    family: The cluster parameter group family (e.g. "docdb8.0")
    engine_version: The engine version (e.g. "8.0.0")
    """

    def __init__(
        self,
        instance_type: ec2.InstanceType,
        master_username: str,
        port: int,
        family: str,
        engine_version: str,
    ) -> None:
        self.instance_type = instance_type
        self.master_username = master_username
        self.port = port
        self.family = family
        self.engine_version = engine_version
