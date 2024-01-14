import boto3
import json

s3 = boto3.client('s3')


def list_files_in_s3(bucket: str, prefix: str):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    files = response.get("Contents")
    return [file["Key"] for file in files]


def read_json_file_in_s3(bucket: str, prefix: str) -> dict:
    result = s3.list_objects(Bucket=bucket, Prefix=prefix)
    for file in result.get('Contents'):
        data = s3.get_object(Bucket=bucket, Key=file.get('Key'))
        contents = data['Body'].read()
        return json.loads(contents.decode("utf-8"))
