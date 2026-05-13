"""Tests for the SSM client wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from envault.ssm import SSMClient, SSMError


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "op")


@pytest.fixture()
def ssm_client():
    with patch("envault.ssm.boto3.Session") as mock_session:
        mock_boto = MagicMock()
        mock_session.return_value.client.return_value = mock_boto
        client = SSMClient(region="us-east-1")
        client._client = mock_boto
        yield client, mock_boto


def test_get_parameter_success(ssm_client):
    client, mock_boto = ssm_client
    mock_boto.get_parameter.return_value = {"Parameter": {"Value": "secret123"}}
    assert client.get_parameter("/app/db_password") == "secret123"
    mock_boto.get_parameter.assert_called_once_with(
        Name="/app/db_password", WithDecryption=True
    )


def test_get_parameter_not_found_raises(ssm_client):
    client, mock_boto = ssm_client
    mock_boto.get_parameter.side_effect = _client_error("ParameterNotFound")
    with pytest.raises(SSMError, match="Parameter not found"):
        client.get_parameter("/missing/param")


def test_get_parameter_other_error_raises(ssm_client):
    client, mock_boto = ssm_client
    mock_boto.get_parameter.side_effect = _client_error("AccessDeniedException")
    with pytest.raises(SSMError, match="AccessDeniedException"):
        client.get_parameter("/app/secret")


def test_get_parameters_by_path(ssm_client):
    client, mock_boto = ssm_client
    paginator_mock = MagicMock()
    paginator_mock.paginate.return_value = [
        {
            "Parameters": [
                {"Name": "/prod/DB_HOST", "Value": "localhost"},
                {"Name": "/prod/DB_PORT", "Value": "5432"},
            ]
        }
    ]
    mock_boto.get_paginator.return_value = paginator_mock
    result = client.get_parameters_by_path("/prod")
    assert result == {"DB_HOST": "localhost", "DB_PORT": "5432"}


def test_get_parameters_by_path_error_raises(ssm_client):
    client, mock_boto = ssm_client
    paginator_mock = MagicMock()
    paginator_mock.paginate.side_effect = _client_error("AccessDeniedException")
    mock_boto.get_paginator.return_value = paginator_mock
    with pytest.raises(SSMError, match="/prod"):
        client.get_parameters_by_path("/prod")


def test_get_parameters_empty_list(ssm_client):
    client, _ = ssm_client
    assert client.get_parameters([]) == {}


def test_get_parameters_chunks(ssm_client):
    client, mock_boto = ssm_client
    names = [f"/app/KEY_{i}" for i in range(12)]
    mock_boto.get_parameters.return_value = {
        "Parameters": [{"Name": n, "Value": f"val_{i}"} for i, n in enumerate(names[:10])],
        "InvalidParameters": [],
    }
    result = client.get_parameters(names[:10])
    assert len(result) == 10
    assert mock_boto.get_parameters.call_count == 1
