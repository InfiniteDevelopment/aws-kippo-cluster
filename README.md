# AWS Kippo Cluster

[![Build Status](https://travis-ci.org/cdodd/aws-kippo-cluster.svg?branch=master)](https://travis-ci.org/cdodd/aws-kippo-cluster)

This repo contains a CloudFormation template (`aws-kippo-cluster.json`) that
creates a highly available, scalable
[kippo](https://github.com/desaster/kippo) honeypot cluster, with
[Kippo-Graph](https://github.com/ikoniaris/kippo-graph) installed.

The CloudFormation template creates the following:
* A MySQL RDS instance to store the data collected by kippo
* An Auto Scaling group for the kippo sensors
* An Elastic load balancer in front of the kippo sensors for serving Kippo-Graph
  content

The CloudFormation template assumes that you have a VPC configured with at
least two subnets in different Availability Zones.

## Creating the kippo cluster
You can create the kippo cluster by either uploading the CloudFormation
template through the web interface in the AWS console, or on the command line
using [`awscli`](http://aws.amazon.com/cli/) (refer to the
[AWS documentation](http://docs.aws.amazon.com/cli/latest/userguide/installing.html)
for installation instructions).

To run the template on the command line use the following command:
```
aws cloudformation create-stack \
  --stack-name kippo-cluster \
  --template-body file://aws-kippo-cluster.json \
  --parameters \
    ParameterKey=Ec2InstanceType,ParameterValue=t2.micro \
    ParameterKey=Ec2SubnetIdList,ParameterValue=[subnet-xxxxxxxx,subnet-xxxxxxxx] \
    ParameterKey=ElbSubnetIdList,ParameterValue=[subnet-xxxxxxxx,subnet-xxxxxxxx] \
    ParameterKey=KeyName,ParameterValue=YourKeypair \
    ParameterKey=KippoSensorCount,ParameterValue=3 \
    ParameterKey=RdsInstanceType,ParameterValue=db.t2.micro \
    ParameterKey=RdsRootPassword,ParameterValue=YourRdsPassword \
    ParameterKey=RdsStorage,ParameterValue=30 \
    ParameterKey=RdsSubnetIdList,ParameterValue=[subnet-xxxxxxxx,subnet-xxxxxxxx] \
    ParameterKey=RealSshPort,ParameterValue=7777 \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxxxxx
```

Once the CloudFormation stack has been created and the kippo sensors are showing
as `InService` in the ELB, you can find the hostname to access Kippo-Graph by
checking the `ElbEndpoint` output of the stack. An example URL would be:
`http://kippo-cluster-elb-f3vgxegw7kb4-1143453499.eu-west-1.elb.amazonaws.com/kippo-graph/`

If you have a your own domain name, you can CNAME a record to the ELB hostname.

## Generate the CloudFormation template
The CloudFormation template for the kippo cluster was generated using the
[`troposphere`](https://github.com/cloudtools/troposphere) python module.
Creating CloudFormation templates using python code is much nicer than dealing
with raw JSON, you can break the code up into logical sections, add comments,
pull data from external sources and make use conditional and looping
constructs.

Assuming you have [`pip`](https://pypi.python.org/pypi/pip) installed you can
install troposphere by running `sudo pip install troposphere`.

Once troposphere is installed you can generate the template by running
`./generate_cf_template.py > aws-kippo-cluster.json`
