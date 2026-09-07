import boto3
from botocore.config import Config
from ecg_service.config import S3_BUCKET, S3_REGION

_s3 = boto3.client(
    "s3",
    region_name=S3_REGION,
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


def upload_and_get_link(file_path: str, key: str, expires_in: int = 86400) -> str:
    """Upload a file to S3 and return a time-limited presigned download URL."""
    _s3.upload_file(file_path, S3_BUCKET, key)
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )