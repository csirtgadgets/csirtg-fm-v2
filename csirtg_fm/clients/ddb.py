# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html

from pprint import pprint
import boto3
from botocore.exceptions import ClientError
import os

DB = boto3.resource('dynamodb', region_name='us-east-1')

TABLE = os.getenv('DYNAMODB_TABLE', 'test2')
TABLE = DB.Table(TABLE)
from time import time

class Client(object):

    def indicators_create(self, data):
        data = [d.__dict__() for d in data]

        retry = []
        added = set()
        with TABLE.batch_writer() as batch:

            for idx, v in enumerate(data):
                if not data[idx].get('last_at'):
                    data[idx]['last_at'] = data[idx]['reported_at']
                data[idx]['ip'] = data[idx]['indicator']
                data[idx]['ts'] = \
                    data[idx]['last_at'] + ':' + data[idx]['ip'] + ':' + data[idx]['provider'] \
                    + ':' + data[idx]['group'] + ':' \
                    + ''.join(data[idx]['tags'])
                data[idx]['confidence'] = int(data[idx]['confidence'])

                if data[idx]['ts'] in added:
                    continue

                added.add(data[idx]['ts'])
                data[idx]['created_at'] = int(time())
                try:
                    batch.put_item(
                        Item=data[idx]
                    )
                except ClientError as e:
                  retry += data

        #
        # if len(retry) > 0:
        #     for idx, v in enumerate(data):
        #         if not data[idx].get('last_at'):
        #             data[idx]['last_at'] = data[idx]['reported_at']
        #         data[idx]['ip'] = data[idx]['indicator']
        #         data[idx]['ts'] = \
        #             data[idx]['last_at'] + ':' + data[idx]['provider'] \
        #             + ':' + data[idx]['group'] + ':' \
        #             + ''.join(data[idx]['tags'])
        #         data[idx]['confidence'] = int(data[idx]['confidence'])
        #
        #         try:
        #             batch.put_item(
        #                 Item=data[idx]
        #             )
        #         except ClientError as e:
        #             pprint(data[idx])

Plugin = Client
