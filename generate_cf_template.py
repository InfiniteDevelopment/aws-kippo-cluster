#!/usr/bin/env python

# 3rd party modules
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Parameter, Ref
from troposphere import Template
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration, Tag
from troposphere.ec2 import SecurityGroup, SecurityGroupRule
from troposphere.elasticloadbalancing import HealthCheck, Listener
from troposphere.elasticloadbalancing import LoadBalancer
from troposphere.rds import DBInstance, DBSubnetGroup


class CreateTemplate(object):
    def __init__(self):
        self.start_template()
        self.add_mappings()
        self.add_parameters()
        self.add_security_groups()
        self.add_kippo_rds()
        self.add_kippo_sensors()

    def start_template(self):
        self.template = Template()
        self.template.add_version('2010-09-09')
        self.template.add_description('Kippo cluster CloudFormation stack')

    def add_mappings(self):
        # Ubuntu Trusty 14.04 LTS amd64
        self.template.add_mapping('Ec2AmiMap', {
            'ap-northeast-1': {'AmiId': 'ami-c011d4c0'},
            'ap-southeast-1': {'AmiId': 'ami-76546924'},
            'eu-central-1': {'AmiId': 'ami-00dae61d'},
            'eu-west-1': {'AmiId': 'ami-2396f654'},
            'sa-east-1': {'AmiId': 'ami-75b23768'},
            'us-east-1': {'AmiId': 'ami-f63b3e9e'},
            'us-west-1': {'AmiId': 'ami-057f9d41'},
            'cn-north-1': {'AmiId': 'ami-78d84541'},
            'us-gov-west-1': {'AmiId': 'ami-85fa9ba6'},
        })

    def add_parameters(self):

        self.template.add_parameter(Parameter(
            'Ec2InstanceType',
            Default='t2.micro',
            Description='Instance type of the EC2 instances',
            Type='String',
        ))
        self.template.add_parameter(Parameter(
            'Ec2SubnetIdList',
            Description='List of subnet IDs in which to create the EC2 instances',
            Type='List<AWS::EC2::Subnet::Id>',
        ))
        self.template.add_parameter(Parameter(
            'ElbSubnetIdList',
            Description='List of subnet IDs in which to create the ELB',
            Type='List<AWS::EC2::Subnet::Id>',
        ))
        self.template.add_parameter(Parameter(
            'KeyName',
            Description='Name of the keypair to install on the EC2 instances',
            Type='AWS::EC2::KeyPair::KeyName',
        ))
        self.template.add_parameter(Parameter(
            'KippoSensorCount',
            Default='1',
            Description='Number of kippo sensors to create',
            Type='Number',
        ))
        self.template.add_parameter(Parameter(
            'RdsInstanceType',
            Default='t2.micro',
            Description='Instance type of the RDS instance',
            Type='String',
        ))
        self.template.add_parameter(Parameter(
            'RdsRootPassword',
            Description='Password to use for the root RDS user',
            Type='String',
        ))
        self.template.add_parameter(Parameter(
            'RdsStorage',
            Default='20',
            Description='Amount of storage (GB) for the RDS instance',
            Type='Number',
        ))
        self.template.add_parameter(Parameter(
            'RdsSubnetIdList',
            Description='List of subnet IDs in which to create the RDS instance',
            Type='List<AWS::EC2::Subnet::Id>',
        ))
        self.template.add_parameter(Parameter(
            'RealSshPort',
            Description='Port number to use for the real SSH service',
            Type='Number',
        ))
        self.template.add_parameter(Parameter(
            'VpcId',
            Description='ID of the VPC in which to create the kippo cluster',
            Type='AWS::EC2::VPC::Id',
        ))

    def add_security_groups(self):
        # kippo sensor EC2 security group
        self.template.add_resource(SecurityGroup(
            'Ec2SecurityGroup',
            GroupDescription='Security group for the kippo sensor ASG',
            SecurityGroupIngress=[
                # Allow SSH (to kippo) from anywhere
                SecurityGroupRule(
                    CidrIp='0.0.0.0/0',
                    FromPort=22,
                    ToPort=22,
                    IpProtocol='tcp',
                ),
                # Allow real SSH from anywhere
                SecurityGroupRule(
                    CidrIp='0.0.0.0/0',
                    FromPort=Ref('RealSshPort'),
                    ToPort=Ref('RealSshPort'),
                    IpProtocol='tcp',
                ),
                # Allow HTTP from the kippo ELB
                SecurityGroupRule(
                    FromPort=80,
                    ToPort=80,
                    IpProtocol='tcp',
                    SourceSecurityGroupId=Ref('ElbSecurityGroup'),
                ),
                # Allow HTTPS from the kippo ELB
                SecurityGroupRule(
                    FromPort=443,
                    ToPort=443,
                    IpProtocol='tcp',
                    SourceSecurityGroupId=Ref('ElbSecurityGroup'),
                ),
            ],
            VpcId=Ref('VpcId'),
        ))

        # kippo sensor ELB security group
        self.template.add_resource(SecurityGroup(
            'ElbSecurityGroup',
            GroupDescription='Security group for the kippo sensor ELB',
            SecurityGroupIngress=[
                # Allow HTTP from anywhere
                SecurityGroupRule(
                    CidrIp='0.0.0.0/0',
                    FromPort=80,
                    ToPort=80,
                    IpProtocol='tcp',
                ),
                # Allow HTTPS from anywhere
                SecurityGroupRule(
                    CidrIp='0.0.0.0/0',
                    FromPort=443,
                    ToPort=443,
                    IpProtocol='tcp',
                ),
            ],
            VpcId=Ref('VpcId'),
        ))

        # RDS security group
        self.template.add_resource(SecurityGroup(
            'RdsSecurityGroup',
            VpcId=Ref('VpcId'),
            GroupDescription='Security group for the kippo RDS instance',
            SecurityGroupIngress=[
                # Allow MySQL from kippo EC2 instances
                SecurityGroupRule(
                    FromPort=3306,
                    ToPort=3306,
                    IpProtocol='tcp',
                    SourceSecurityGroupId=Ref('Ec2SecurityGroup'),
                ),
            ],
        ))

    def add_kippo_rds(self):
        self.template.add_resource(DBSubnetGroup(
            'RdsSubnetGroup',
            DBSubnetGroupDescription='Subnet group for the kippo RDS instance',
            SubnetIds=Ref('RdsSubnetIdList'),
        ))

        self.template.add_resource(DBInstance(
            'RdsInstance',
            AllocatedStorage=Ref('RdsStorage'),
            DBInstanceClass=Ref('RdsInstanceType'),
            DBInstanceIdentifier='kippo-database',
            DBSubnetGroupName=Ref('RdsSubnetGroup'),
            Engine='MySQL',
            EngineVersion='5.6.22',
            MasterUsername='root',
            MasterUserPassword=Ref('RdsRootPassword'),
            MultiAZ=True,
            Port=3306,
            VPCSecurityGroups=[Ref('RdsSecurityGroup')],
        ))

        self.template.add_output(Output(
            'RdsEndpoint',
            Description='RDS endpoint address',
            Value=GetAtt('RdsInstance', 'Endpoint.Address'),
        ))

    def add_kippo_sensors(self):
        # Create the ELB
        self.template.add_resource(LoadBalancer(
            'Elb',
            Listeners=[
                Listener(
                    InstancePort=80,
                    LoadBalancerPort=80,
                    Protocol='http',
                ),
                Listener(
                    InstancePort=443,
                    LoadBalancerPort=443,
                    Protocol='tcp',    # Plain TCP forwarding for HTTPS/SSL
                ),
            ],
            CrossZone=True,
            Subnets=Ref('ElbSubnetIdList'),
            SecurityGroups=[Ref('ElbSecurityGroup')],
            Scheme='internet-facing',
            HealthCheck=HealthCheck(
                Target='HTTP:80/kippo-graph/',
                HealthyThreshold=2,
                UnhealthyThreshold=5,
                Interval=120,
                Timeout=60,
            ),
        ))

        self.template.add_output(Output(
            'ElbEndpoint',
            Description='ELB endpoint address',
            Value=GetAtt('Elb', 'DNSName'),
        ))

        self.template.add_resource(LaunchConfiguration(
            'LaunchConfiguration',
            KeyName=Ref('KeyName'),
            ImageId=FindInMap('Ec2AmiMap', Ref('AWS::Region'), 'AmiId'),
            InstanceType=Ref('Ec2InstanceType'),
            SecurityGroups=[Ref('Ec2SecurityGroup')],
            AssociatePublicIpAddress=True,
            UserData=Base64(Join('\n', [
                '#cloud-config',
                'repo_upgrade: security',
                'runcmd:',
                ' - "/usr/bin/wget -O /tmp/configure_kippo_sensor.sh https://raw.githubusercontent.com/cdodd/aws-kippo-cluster/master/bootstrap/configure_kippo_sensor.sh"',
                Join(
                    '',
                    [
                        ' - "bash /tmp/configure_kippo_sensor.sh',
                        ' ',
                        GetAtt('RdsInstance', 'Endpoint.Address'),
                        ' ',
                        Ref('RdsRootPassword'),
                        ' ',
                        Ref('RealSshPort'),
                        '"',
                    ],
                ),
            ])),
        ))

        self.template.add_resource(AutoScalingGroup(
            'Asg',
            DesiredCapacity=Ref('KippoSensorCount'),
            HealthCheckGracePeriod=1800,
            HealthCheckType='ELB',
            LaunchConfigurationName=Ref('LaunchConfiguration'),
            LoadBalancerNames=[Ref('Elb')],
            MaxSize=Ref('KippoSensorCount'),
            MinSize=Ref('KippoSensorCount'),
            Tags=[Tag(key='Name', value='kippo-sensor', propogate='true')],
            VPCZoneIdentifier=Ref('Ec2SubnetIdList'),
        ))

    def output_template(self):
        return self.template.to_json()

if __name__ == '__main__':
    print(CreateTemplate().output_template())
