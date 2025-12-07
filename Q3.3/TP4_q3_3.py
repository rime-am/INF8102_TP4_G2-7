import json
import uuid
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
STACK_NAME = "S3BucketStack"

# Bucket source 
BUCKET_NAME = "polystudentstacks3"

# Bucket destination
DEST_BUCKET_NAME = "polystudentstacks3-back" 

KMS_ARN = "arn:aws:kms:us-east-1:807867956908:key/mrk-e22f95147c534236b2220a1d7062413b"

# Bucket de logs CloudTrail 
CT_LOG_BUCKET = f"polystudents3-ct-logs-{uuid.uuid4().hex[:6]}"

cloudformation = boto3.client("cloudformation", region_name=REGION)

def stack_exists(name: str) -> bool:
    try:
        cloudformation.describe_stacks(StackName=name)
        return True
    except ClientError as e:
        return "does not exist" not in str(e)

s3_cloudtrail_template = {
  "AWSTemplateFormatVersion": "2010-09-09",
  "Description": "S3 replication + CloudTrail (object write/delete)",
  "Resources": {
    # 1) Bucket destination (backup)
    "DestinationBucket": {
      "Type": "AWS::S3::Bucket",
      "DeletionPolicy": "Retain",
      "Properties": {
        "BucketName": DEST_BUCKET_NAME,
        "AccessControl": "Private",
        "PublicAccessBlockConfiguration": {
          "BlockPublicAcls": True,
          "BlockPublicPolicy": True,
          "IgnorePublicAcls": True,
          "RestrictPublicBuckets": True
        },
        "BucketEncryption": {
          "ServerSideEncryptionConfiguration": [{
            "ServerSideEncryptionByDefault": {
              "SSEAlgorithm": "aws:kms",
              "KMSMasterKeyID": KMS_ARN
            }
          }]
        },
        "VersioningConfiguration": { "Status": "Enabled" }
      }
    },

    # Role IAM pour la réplication
    "ReplicationRole": {
      "Type": "AWS::IAM::Role",
      "Properties": {
        "AssumeRolePolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "s3.amazonaws.com"},
            "Action": "sts:AssumeRole"
          }]
        },
        "Policies": [{
          "PolicyName": "S3ReplicationPolicy",
          "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
              {
                "Effect": "Allow",
                "Action": ["s3:GetReplicationConfiguration","s3:ListBucket","s3:GetBucketVersioning"],
                "Resource": { "Fn::Join": ["", ["arn:aws:s3:::", BUCKET_NAME]] }
              },
              {
                "Effect": "Allow",
                "Action": [
                  "s3:GetObjectVersion","s3:GetObjectVersionAcl","s3:GetObjectVersionTagging",
                  "s3:GetObjectVersionForReplication"
                ],
                "Resource": { "Fn::Join": ["", ["arn:aws:s3:::", BUCKET_NAME, "/*"]] }
              },
              {
                "Effect": "Allow",
                "Action": [
                  "s3:ReplicateObject","s3:ReplicateDelete","s3:ReplicateTags",
                  "s3:ObjectOwnerOverrideToBucketOwner"
                ],
                "Resource": { "Fn::Join": ["", [{"Fn::GetAtt": ["DestinationBucket","Arn"]}, "/*"]] }
              },
              {
                "Effect": "Allow",
                "Action": ["kms:Decrypt","kms:Encrypt","kms:ReEncrypt*","kms:GenerateDataKey*","kms:DescribeKey"],
                "Resource": KMS_ARN
              }
            ]
          }
        }]
      }
    },

    # Bucket source avec ReplicationConfiguration
    "S3Bucket": {
      "Type": "AWS::S3::Bucket",
      "DependsOn": ["DestinationBucket", "ReplicationRole"],
      "DeletionPolicy": "Retain",
      "Properties": {
        "BucketName": BUCKET_NAME,
        "AccessControl": "Private",
        "PublicAccessBlockConfiguration": {
          "BlockPublicAcls": True,
          "BlockPublicPolicy": True,
          "IgnorePublicAcls": True,
          "RestrictPublicBuckets": True
        },
        "BucketEncryption": {
          "ServerSideEncryptionConfiguration": [{
            "ServerSideEncryptionByDefault": {
              "SSEAlgorithm": "aws:kms",
              "KMSMasterKeyID": KMS_ARN
            }
          }]
        },
        "VersioningConfiguration": { "Status": "Enabled" },

        "ReplicationConfiguration": {
          "Role": { "Fn::GetAtt": ["ReplicationRole","Arn"] },
          "Rules": [{
            "Id": "ReplicateAll",
            "Status": "Enabled",
            "Priority": 1,
            "Filter": {},
            "SourceSelectionCriteria": {"SseKmsEncryptedObjects": {"Status": "Enabled"}},
            "Destination": {
              "Bucket": { "Fn::GetAtt": ["DestinationBucket","Arn"] },
              "EncryptionConfiguration": {"ReplicaKmsKeyID": KMS_ARN}
            },
            "DeleteMarkerReplication": {"Status": "Enabled"}
          }]
        }
      }
    },

    # Bucket pour logs CloudTrail + policy
    "CloudTrailLogBucket": {
      "Type": "AWS::S3::Bucket",
      "DeletionPolicy": "Retain",
      "Properties": {
        "BucketName": CT_LOG_BUCKET,
        "AccessControl": "Private",
        "PublicAccessBlockConfiguration": {
          "BlockPublicAcls": True,
          "BlockPublicPolicy": True,
          "IgnorePublicAcls": True,
          "RestrictPublicBuckets": True
        }
      }
    },
    "CloudTrailLogBucketPolicy": {
      "Type": "AWS::S3::BucketPolicy",
      "Properties": {
        "Bucket": {"Ref": "CloudTrailLogBucket"},
        "PolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Sid": "AWSCloudTrailAclCheck",
              "Effect": "Allow",
              "Principal": {"Service": "cloudtrail.amazonaws.com"},
              "Action": "s3:GetBucketAcl",
              "Resource": {"Fn::GetAtt": ["CloudTrailLogBucket","Arn"]}
            },
            {
              "Sid": "AWSCloudTrailWrite",
              "Effect": "Allow",
              "Principal": {"Service": "cloudtrail.amazonaws.com"},
              "Action": "s3:PutObject",
              "Resource": {"Fn::Join": ["", [
                {"Fn::GetAtt": ["CloudTrailLogBucket","Arn"]},
                "/AWSLogs/", {"Ref":"AWS::AccountId"}, "/*"
              ]]},
              "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
            }
          ]
        }
      }
    },

    #  CloudTrail (Data events WriteOnly sur objets du bucket source)
    "Polystudents3CloudTrail": {
      "Type": "AWS::CloudTrail::Trail",
      "DependsOn": ["CloudTrailLogBucketPolicy"],
      "Properties": {
        "TrailName": "Polystudents3CloudTrail",
        "IsLogging": True,
        "S3BucketName": {"Ref": "CloudTrailLogBucket"},
        "EnableLogFileValidation": True,
        "IsMultiRegionTrail": False,
        "EventSelectors": [{
          "ReadWriteType": "WriteOnly",
          "IncludeManagementEvents": True,
          "DataResources": [{
            "Type": "AWS::S3::Object",
            "Values": [{
              "Fn::Join": ["", ["arn:aws:s3:::", {"Ref":"S3Bucket"}, "/"]]
            }]
          }]
        }]
      }
    }
  },
  "Outputs": {
    "SourceBucket": {"Value": {"Ref": "S3Bucket"}},
    "DestinationBucket": {"Value": {"Ref": "DestinationBucket"}},
    "CloudTrailLogBucket": {"Value": {"Ref": "CloudTrailLogBucket"}},
    "TrailName": {"Value": {"Ref": "Polystudents3CloudTrail"}}
  }
}

template_body = json.dumps(s3_cloudtrail_template)

cloudformation.validate_template(TemplateBody=template_body)

try:
    if stack_exists(STACK_NAME):
        cloudformation.update_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Capabilities=["CAPABILITY_NAMED_IAM"]
        )
        cloudformation.get_waiter("stack_update_complete").wait(StackName=STACK_NAME)
        print("UPDATE_COMPLETE")
    else:
        resp = cloudformation.create_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Capabilities=["CAPABILITY_NAMED_IAM"]
        )
        print("Stack creation initiated. Stack ID:", resp["StackId"])
        cloudformation.get_waiter("stack_create_complete").wait(StackName=STACK_NAME)
        print("CREATE_COMPLETE")

except ClientError as e:
    # si "No updates are to be performed"
    print("An error occurred:", e)
except Exception as e:
    print("An error occurred:", e)
