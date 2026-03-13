"""
storage/object_store.py — S3-compatible object store for artifacts.
Handles code bundles, media files, PDFs, and other binary artifacts.
"""
from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, BinaryIO, Dict, Optional

import boto3
from botocore.client import Config

logger = logging.getLogger(__name__)


class ObjectStore:
    """
    Thin wrapper around S3 (or MinIO for local dev) for artifact storage.
    All artifacts are stored with provenance metadata.
    """

    def __init__(self):
        self.bucket = os.getenv("S3_BUCKET", "ai-office-artifacts")
        self.s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT", "http://minio:9000"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minioadmin"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
            region_name=os.getenv("S3_REGION", "us-east-1"),
            config=Config(signature_version="s3v4"),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.s3.create_bucket(Bucket=self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
            except Exception as e:
                logger.error(f"Failed to create bucket: {e}")

    def store(
        self,
        key: str,
        content: bytes | str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Store content at key. Returns the full object URI.
        Metadata is stored as S3 user metadata (str values only).
        """
        if isinstance(content, str):
            content = content.encode("utf-8")

        meta = {
            "stored_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        # S3 metadata values must be strings
        meta = {k: str(v) for k, v in meta.items()}

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata=meta,
        )
        uri = f"object://s3/{self.bucket}/{key}"
        logger.info(f"Stored artifact: {uri}")
        return uri

    def retrieve(self, key: str) -> bytes:
        """Retrieve raw bytes for an artifact."""
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def retrieve_text(self, key: str) -> str:
        return self.retrieve(key).decode("utf-8")

    def get_metadata(self, key: str) -> Dict[str, str]:
        response = self.s3.head_object(Bucket=self.bucket, Key=key)
        return response.get("Metadata", {})

    def store_json(
        self,
        key: str,
        data: Any,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        return self.store(
            key,
            json.dumps(data, indent=2, default=str),
            content_type="application/json",
            metadata=metadata,
        )

    def store_code(
        self,
        artifact_id: str,
        filename: str,
        code: str,
        language: str = "python",
        task_id: str = "",
        agent_id: str = "",
    ) -> str:
        key = f"code/{artifact_id}/{filename}"
        return self.store(
            key,
            code,
            content_type="text/plain",
            metadata={
                "language": language,
                "task_id": task_id,
                "agent_id": agent_id,
            },
        )

    def get_presigned_url(self, key: str, expiry: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expiry,
        )

    def list_artifacts(self, prefix: str = "") -> list:
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]
