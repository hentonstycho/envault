"""AWS SSM Parameter Store client for fetching secrets."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class SSMError(Exception):
    """Raised when SSM operations fail."""


class SSMClient:
    """Thin wrapper around boto3 SSM client for fetching parameters."""

    def __init__(self, region: str, profile: Optional[str] = None) -> None:
        self.region = region
        session_kwargs: Dict = {"region_name": region}
        if profile:
            session_kwargs["profile_name"] = profile
        try:
            session = boto3.Session(**session_kwargs)
            self._client = session.client("ssm")
        except NoCredentialsError as exc:
            raise SSMError("AWS credentials not found.") from exc

    def get_parameter(self, name: str, decrypt: bool = True) -> str:
        """Fetch a single SSM parameter value by name."""
        try:
            response = self._client.get_parameter(
                Name=name, WithDecryption=decrypt
            )
            return response["Parameter"]["Value"]
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "ParameterNotFound":
                raise SSMError(f"Parameter not found: {name}") from exc
            raise SSMError(f"Failed to fetch parameter '{name}': {code}") from exc

    def get_parameters_by_path(self, path: str, decrypt: bool = True) -> Dict[str, str]:
        """Fetch all SSM parameters under a given path prefix."""
        results: Dict[str, str] = {}
        paginator = self._client.get_paginator("get_parameters_by_path")
        try:
            for page in paginator.paginate(
                Path=path,
                Recursive=True,
                WithDecryption=decrypt,
            ):
                for param in page.get("Parameters", []):
                    key = param["Name"].removeprefix(path).lstrip("/")
                    results[key] = param["Value"]
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            raise SSMError(f"Failed to fetch path '{path}': {code}") from exc
        logger.debug("Fetched %d parameters from path '%s'", len(results), path)
        return results

    def get_parameters(self, names: List[str], decrypt: bool = True) -> Dict[str, str]:
        """Fetch multiple SSM parameters by explicit name list."""
        if not names:
            return {}
        results: Dict[str, str] = {}
        # SSM allows max 10 names per request
        for i in range(0, len(names), 10):
            chunk = names[i : i + 10]
            try:
                response = self._client.get_parameters(
                    Names=chunk, WithDecryption=decrypt
                )
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                raise SSMError(f"Failed to fetch parameters: {code}") from exc
            for param in response.get("Parameters", []):
                results[param["Name"]] = param["Value"]
            invalid = response.get("InvalidParameters", [])
            if invalid:
                logger.warning("Invalid/missing parameters: %s", invalid)
        return results
