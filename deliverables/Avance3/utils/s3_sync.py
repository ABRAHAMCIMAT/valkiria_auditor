import os
import glob
import urllib3
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from dotenv import load_dotenv

# Suppress SSL warnings (proxy/firewall intercepts HTTPS in dev environment)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from .env file
load_dotenv()

# Create the boto3 client for S3
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
AWS_PROFILE = os.environ.get("AWS_PROFILE", "Developer")
session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
s3_client = session.client("s3", verify=False)

# Bucket name from .env or default
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

# Folder structure within the bucket
FOLDERS = ["raw/", "processed/", "analytical/"]


def create_bucket_structure(bucket_name: str = BUCKET_NAME) -> None:
    """
    Create bucket folder structure if it does not exist.
    Structure:
      - raw/
      - processed/
      - analytical/

    S3 doesn't have real folders, so we create zero-byte objects as placeholders.
    put_object is idempotent — safe to call even if the prefix already exists.
    """
    for folder in FOLDERS:
        try:
            s3_client.put_object(Bucket=bucket_name, Key=folder, Body=b"")
            print(f"  [ok] s3://{bucket_name}/{folder}")
        except ClientError as e:
            print(f"  [error] s3://{bucket_name}/{folder}: {e}")


def upload_files_to_raw(
    local_path: str,
    bucket_name: str = BUCKET_NAME,
    prefix: str = "raw/",
    file_patterns: list[str] | None = None,
) -> list[str]:
    """
    Upload files to the /raw/ folder within the S3 bucket.

    Args:
        local_path: Local directory or file path to upload.
        bucket_name: Target S3 bucket name.
        prefix: S3 key prefix (default: 'raw/').
        file_patterns: Optional list of glob patterns to filter files
                       (e.g., ['*.pdf', '*.docx']). If None, uploads all files.

    Returns:
        List of S3 keys that were uploaded.
    """
    uploaded_keys = []

    if os.path.isfile(local_path):
        # Single file upload
        file_name = os.path.basename(local_path)
        s3_key = f"{prefix}{file_name}"
        s3_client.upload_file(local_path, bucket_name, s3_key)
        uploaded_keys.append(s3_key)
        print(f"  [uploaded] {local_path} -> s3://{bucket_name}/{s3_key}")

    elif os.path.isdir(local_path):
        # Directory upload — collect files matching patterns
        if file_patterns:
            files = []
            for pattern in file_patterns:
                files.extend(glob.glob(os.path.join(local_path, "**", pattern), recursive=True))
        else:
            files = [
                os.path.join(root, f)
                for root, _, filenames in os.walk(local_path)
                for f in filenames
            ]

        for file_path in sorted(set(files)):
            # Preserve relative directory structure under the prefix
            relative_path = os.path.relpath(file_path, local_path)
            s3_key = f"{prefix}{relative_path.replace(os.sep, '/')}"
            s3_client.upload_file(file_path, bucket_name, s3_key)
            uploaded_keys.append(s3_key)
            print(f"  [uploaded] {file_path} -> s3://{bucket_name}/{s3_key}")
    else:
        raise FileNotFoundError(f"Path not found: {local_path}")

    print(f"\n  Total files uploaded: {len(uploaded_keys)}")
    return uploaded_keys


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="S3 sync utility for ISO 27001 data bucket")
    parser.add_argument("--bucket", default=BUCKET_NAME, help="S3 bucket name")
    parser.add_argument("--init", action="store_true", help="Create bucket folder structure")
    parser.add_argument("--upload", type=str, help="Local path (file or directory) to upload to raw/")
    parser.add_argument(
        "--patterns",
        nargs="*",
        default=None,
        help="File glob patterns to filter uploads (e.g., '*.pdf' '*.docx')",
    )

    args = parser.parse_args()

    if args.init:
        print(f"Initializing folder structure in s3://{args.bucket}/")
        create_bucket_structure(args.bucket)

    if args.upload:
        print(f"\nUploading to s3://{args.bucket}/raw/")
        upload_files_to_raw(args.upload, bucket_name=args.bucket, file_patterns=args.patterns)

    if not args.init and not args.upload:
        parser.print_help()
