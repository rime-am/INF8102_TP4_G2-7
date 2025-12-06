from troposphere import Template, Ref, Sub, Join, GetAtt, Select, GetAZs, Parameter, ec2, Tag, Output

t = Template()
t.set_description("Question 1")

#Parameters
env_name = t.add_parameter(
    Parameter(
        "EnvironmentName",
        Type="String",
        Description="Environment prefix",
        Default="Q1_TP4"
    )
)

vpc_cidr = t.add_parameter(
    Parameter(
        "VpcCIDR", 
        Type="String", 
        Default="10.0.0.0/16",
        Description="VPC polystudent-vpc1" ))

public_subnet1_cidr = t.add_parameter(
    Parameter(
        "PublicSubnet1CIDR", 
        Type="String", 
        Default="10.0.0.0/24",
        Description= "public subnet in Availability Zone 1"))

public_subnet2_cidr = t.add_parameter(
    Parameter(
        "PublicSubnet2CIDR", 
        Type="String", 
        Default="10.0.16.0/24",
        Description= "public subnet in Availability Zone 2"))

private_subnet1_cidr = t.add_parameter(
    Parameter(
        "PrivateSubnet1CIDR", 
        Type="String", 
        Default="10.0.128.0/24",
        Description= "private subnet in Availability Zone 1"))

private_subnet2_cidr = t.add_parameter(
    Parameter(
        "PrivateSubnet2CIDR", 
        Type="String", 
        Default="10.0.144.0/24",
        Description= "private subnet in Availability Zone 2"))

# Création des ressources : VPC
vpc = t.add_resource(
    ec2.VPC(
        "VPC",
        CidrBlock=Ref(vpc_cidr),
        EnableDnsSupport=True,
        EnableDnsHostnames=True,
        Tags=[Tag("Name", Ref(env_name))]
    )
)

# Création des ressources : subnets privées et publiques
public_subnet1 = t.add_resource(
    ec2.Subnet(
        "PublicSubnetAZ1",
        VpcId=Ref(vpc),
        CidrBlock=Ref(public_subnet1_cidr),
        MapPublicIpOnLaunch=True,
        AvailabilityZone=Select(0, GetAZs("")),
        Tags=[{"Key": "Name", "Value": Sub("${EnvironmentName} Public Subnet (AZ1)")}]
    )
)

public_subnet2 = t.add_resource(
    ec2.Subnet(
        "PublicSubnetAZ2",
        VpcId=Ref(vpc),
        CidrBlock=Ref(public_subnet2_cidr),
        MapPublicIpOnLaunch=True,
        AvailabilityZone=Select(1, GetAZs("")),
        Tags=[{"Key": "Name", "Value": Sub("${EnvironmentName} Public Subnet (AZ2)")}]
    )
)

private_subnet1 = t.add_resource(
    ec2.Subnet(
        "PrivateSubnetAZ1",
        VpcId=Ref(vpc),
        CidrBlock=Ref(private_subnet1_cidr),
        MapPublicIpOnLaunch=False,
        AvailabilityZone=Select(0, GetAZs("")),
        Tags=[{"Key": "Name", "Value": Sub("${EnvironmentName} Private Subnet (AZ1)")}]
    )
)

private_subnet2 = t.add_resource(
    ec2.Subnet(
        "PrivateSubnetAZ2",
        VpcId=Ref(vpc),
        CidrBlock=Ref(private_subnet2_cidr),
        MapPublicIpOnLaunch=False,
        AvailabilityZone=Select(1, GetAZs("")),
        Tags=[{"Key": "Name", "Value": Sub("${EnvironmentName} Private Subnet (AZ2)")}]
    )
)

# Création des ressources : InternetGateway
igw = t.add_resource(
    ec2.InternetGateway(
        "InternetGateway",
        Tags=[{"Key": "Name", "Value": Ref(env_name)}]
    )
)

t.add_resource(
    ec2.VPCGatewayAttachment(
        "InternetGatewayAttachment",
        VpcId=Ref(vpc),
        InternetGatewayId=Ref(igw)
    )
)

# Création des ressources : Nat Gateway
nat_eip1 = t.add_resource(ec2.EIP("NatGateway1EIP", Domain="vpc"))
nat_eip2 = t.add_resource(ec2.EIP("NatGateway2EIP", Domain="vpc"))

nat_gw1 = t.add_resource(
    ec2.NatGateway(
        "NatGateway1",
        AllocationId=GetAtt(nat_eip1, "AllocationId"),
        SubnetId=Ref(public_subnet1)
    )
)

nat_gw2 = t.add_resource(
    ec2.NatGateway(
        "NatGateway2",
        AllocationId=GetAtt(nat_eip2, "AllocationId"),
        SubnetId=Ref(public_subnet2)
    )
)

# Création des ressources : Route Tables
public_rt = t.add_resource(
    ec2.RouteTable(
        "PublicRouteTable",
        VpcId=Ref(vpc),
         Tags=[{"Key": "Name", "Value": Sub("${EnvironmentName} Public Routes")}]
    )
)

t.add_resource(
    ec2.Route(
        "DefaultPublicRoute",
        RouteTableId=Ref(public_rt),
        DestinationCidrBlock="0.0.0.0/0",
        GatewayId=Ref(igw)
    )
)

t.add_resource(
    ec2.SubnetRouteTableAssociation(
        "PublicSubnetAZ1RouteTableAssociation",
        SubnetId=Ref(public_subnet1),
        RouteTableId=Ref(public_rt)
    )
)

t.add_resource(
    ec2.SubnetRouteTableAssociation(
        "PublicSubnetAZ2RouteTableAssociation",
        SubnetId=Ref(public_subnet2),
        RouteTableId=Ref(public_rt)
    )
)

private_rt1 = t.add_resource(
    ec2.RouteTable(
        "PrivateRouteTableAZ1",
        VpcId=Ref(vpc),
        Tags=[{"Key": "Name", "Value": Sub("${EnvironmentName} Private Routes (AZ1)")}]
    )
)

private_rt2 = t.add_resource(
    ec2.RouteTable(
        "PrivateRouteTableAZ2",
        VpcId=Ref(vpc),
        Tags=[{"Key": "Name", "Value": Sub("${EnvironmentName} Private Routes (AZ2)")}]
    )
)

t.add_resource(
    ec2.Route(
        "DefaultPrivateRouteAZ1",
        RouteTableId=Ref(private_rt1),
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=Ref(nat_gw1)
    )
)

t.add_resource(
    ec2.Route(
        "DefaultPrivateRouteAZ2",
        RouteTableId=Ref(private_rt2),
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=Ref(nat_gw2)
    )
)

t.add_resource(
    ec2.SubnetRouteTableAssociation(
        "PrivateSubnetAZ1RouteTableAssociation",
        SubnetId=Ref(private_subnet1),
        RouteTableId=Ref(private_rt1)
    )
)

t.add_resource(
    ec2.SubnetRouteTableAssociation(
        "PrivateSubnetAZ2RouteTableAssociation",
        SubnetId=Ref(private_subnet2),
        RouteTableId=Ref(private_rt2)
    )
)

# Création des ressources : Security Group
sg = t.add_resource(
    ec2.SecurityGroup(
        "IngressSecurityGroup",
        GroupDescription="Security group allows SSH, HTTP, HTTPS, MSSQL, etc...",
        VpcId=Ref(vpc),
        GroupName= "polystudent-sg-Q1",
        SecurityGroupIngress=[
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=22, ToPort=22, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=80, ToPort=80, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=443, ToPort=443, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=9200, ToPort=9300, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=3389, ToPort=3389, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=3306, ToPort=3306, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=5432, ToPort=5432, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=53, ToPort=53, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="udp", FromPort=53, ToPort=53, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=1433, ToPort=1433, CidrIp="0.0.0.0/0"),
            ec2.SecurityGroupRule(IpProtocol="tcp", FromPort=1514, ToPort=1514, CidrIp="0.0.0.0/0")
        ]
    )
)

# Outputs
t.add_output(
    Output(
        "VPC",
        Description="A reference to the created VPC",
        Value=Ref(vpc)
    )
)

t.add_output(
    Output(
        "PublicSubnets",
        Description="A list of the public subnets",
        Value=Join(",", [Ref(public_subnet1), Ref(public_subnet2)])
    )
)

t.add_output(
    Output(
        "PrivateSubnets",
        Description="A list of the private subnets",
        Value=Join(",", [Ref(private_subnet1), Ref(private_subnet2)])
    )
)

t.add_output(
    Output(
        "PublicSubnetAZ1",
        Description="A reference to the public subnet in Availability Zone 1",
        Value=Ref(public_subnet1)
    )
)

t.add_output(
    Output(
        "PublicSubnetAZ2",
        Description="A reference to the public subnet in Availability Zone 2",
        Value=Ref(public_subnet2)
    )
)

t.add_output(
    Output(
        "PrivateSubnetAZ1",
        Description="A reference to the private subnet in Availability Zone 1",
        Value=Ref(private_subnet1)
    )
)

t.add_output(
    Output(
        "PrivateSubnetAZ2",
        Description="A reference to the private subnet in Availability Zone 2",
        Value=Ref(private_subnet2)
    )
)

# Génération du fichier
with open("Q1/vpc_template.yaml", "w") as f:
    f.write(t.to_yaml())

print("Template générer avec succès!")
