
import json
import boto3

REGION = "us-east-1"  
STACK_NAME = "S3BucketStack"
BUCKET_NAME = "polystudentstacks3" 
KMS_ARN = "arn:aws:kms:us-east-1:807867956908:key/mrk-e22f95147c534236b2220a1d7062413b"

cloudformation = boto3.client("cloudformation", region_name=REGION)

s3_bucket_template = {
  "AWSTemplateFormatVersion": "2010-09-09",
  "Description": "S3 bucket",
  "Resources": {
    "S3Bucket": {
      "DeletionPolicy": "Retain",
      "Type": "AWS::S3::Bucket",
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
          "ServerSideEncryptionConfiguration": [
            {
              "ServerSideEncryptionByDefault": {
                "SSEAlgorithm": "aws:kms",
                "KMSMasterKeyID": KMS_ARN
              }
            }
          ]
        },
        "VersioningConfiguration": { "Status": "Enabled" }
      }
    }
  },
  "Outputs": {
    "S3Bucket": {
      "Description": "Bucket Created! :)",
      "Value": { "Ref": "S3Bucket" }
    }
  }
}

template_body = json.dumps(s3_bucket_template)

# (validation)
cloudformation.validate_template(TemplateBody=template_body)

try:
    response = cloudformation.create_stack(
        StackName=STACK_NAME,
        TemplateBody=template_body
    )
    print(f"Stack creation initiated. Stack ID: {response['StackId']}")
    cloudformation.get_waiter("stack_create_complete").wait(StackName=STACK_NAME)
    print("CREATE_COMPLETE")
except Exception as e:
    print("An error occurred:", e)
