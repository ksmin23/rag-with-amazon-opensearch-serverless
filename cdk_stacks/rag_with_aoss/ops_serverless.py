#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import json

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_iam,
  aws_opensearchserverless as aws_opss
)
from constructs import Construct


class OpsServerlessVectorSearchStack(Stack):

  # def __init__(self, scope: Construct, construct_id: str, sagemaker_execution_role_name, **kwargs) -> None:
  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    user_name = self.node.try_get_context('user_name')
    ops_iam_user = aws_iam.User.from_user_name(self, "OpsAdminUser", user_name)

    collection_name = self.node.try_get_context('collection_name')

    network_security_policy = json.dumps([{
      "Rules": [
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "dashboard"
        },
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "collection"
        }
      ],
      "AllowFromPublic": True
    }], indent=2)

    cfn_network_security_policy = aws_opss.CfnSecurityPolicy(self, "NetworkSecurityPolicy",
      policy=network_security_policy,
      name=f"{collection_name}-security-policy",
      type="network"
    )

    encryption_security_policy = json.dumps({
      "Rules": [
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "collection"
        }
      ],
      "AWSOwnedKey": True
    }, indent=2)

    cfn_encryption_security_policy = aws_opss.CfnSecurityPolicy(self, "EncryptionSecurityPolicy",
      policy=encryption_security_policy,
      name=f"{collection_name}-security-policy",
      type="encryption"
    )

    cfn_collection = aws_opss.CfnCollection(self, "OpssSearchCollection",
      name=collection_name,
      description="Collection to be used for search using OpenSearch Serverless",
      type="VECTORSEARCH" # [SEARCH, TIMESERIES, VECTORSEARCH]
    )
    cfn_collection.add_dependency(cfn_network_security_policy)
    cfn_collection.add_dependency(cfn_encryption_security_policy)

    data_access_policy = json.dumps([
      {
        "Rules": [
          {
            "Resource": [
              f"collection/{collection_name}"
            ],
            "Permission": [
              "aoss:CreateCollectionItems",
              "aoss:DeleteCollectionItems",
              "aoss:UpdateCollectionItems",
              "aoss:DescribeCollectionItems"
            ],
            "ResourceType": "collection"
          },
          {
            "Resource": [
              f"index/{collection_name}/*"
            ],
            "Permission": [
              "aoss:CreateIndex",
              "aoss:DeleteIndex",
              "aoss:UpdateIndex",
              "aoss:DescribeIndex",
              "aoss:ReadDocument",
              "aoss:WriteDocument"
            ],
            "ResourceType": "index"
          }
        ],
        "Principal": [
          ops_iam_user.user_arn
          # , f"arn:aws:sts::{cdk.Aws.ACCOUNT_ID}:assumed-role/{sagemaker_execution_role_name}/*"
        ],
        "Description": "data-access-rule"
      }
    ], indent=2)

    #XXX: max length of policy name is 32
    data_access_policy_name = f"{collection_name}-access-policy"
    assert len(data_access_policy_name) <= 32

    cfn_access_policy = aws_opss.CfnAccessPolicy(self, "OpssDataAccessPolicy",
      name=data_access_policy_name,
      description="Policy for data access",
      policy=data_access_policy,
      type="data"
    )

    cdk.CfnOutput(self, 'OpenSearchDomainEndpoint',
      value=cfn_collection.attr_collection_endpoint,
      export_name=f'{self.stack_name}-OpenSearchDomainEndpoint')
    cdk.CfnOutput(self, 'DashboardsURL',
      value=cfn_collection.attr_dashboard_endpoint,
      export_name=f'{self.stack_name}-DashboardsURL')
