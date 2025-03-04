"""
This module exports some simple names used throughout the CodaLab bundle system:
  - The various CodaLab error classes, with documentation for each.
  - The State class, an enumeration of all legal bundle states.
  - precondition, a utility method that check's a function's input preconditions.
"""
import logging
import os
import re
import http.client
import urllib.request
import urllib.error

from dataclasses import dataclass
from retry import retry
from enum import Enum

from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from google.cloud import storage
import datetime
from codalab.lib.beam.filesystems import (
    AZURE_BLOB_ACCOUNT_NAME,
    AZURE_BLOB_ACCOUNT_KEY,
    AZURE_BLOB_CONTAINER_NAME,
    AZURE_BLOB_HTTP_ENDPOINT,
)

# Increment this on master when ready to cut a release.
# http://semver.org/
CODALAB_VERSION = '1.5.7'
BINARY_PLACEHOLDER = '<binary>'
URLOPEN_TIMEOUT_SECONDS = int(os.environ.get('CODALAB_URLOPEN_TIMEOUT_SECONDS', 5 * 60))

# Silence verbose log outputs from certain libraries
logger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy')
logger.setLevel(logging.WARNING)
logger = logging.getLogger('docker')
logger.setLevel(logging.WARNING)
logger = logging.getLogger('apache_beam')
logger.setLevel(logging.WARNING)


class IntegrityError(ValueError):
    """
    Raised by the model when there is a database integrity issue.

    Indicates a serious error that either means that there was a bug in the model
    code that left the database in a bad state, or that there was an out-of-band
    database edit with the same result.
    """


class PreconditionViolation(ValueError):
    """
    Raised when a value generated by one module fails to satisfy a precondition
    required by another module.

    This class of error is serious and should indicate a problem in code, but it
    it is not an AssertionError because it is not local to a single module.
    """


class UsageError(ValueError):
    """
    Raised when user input causes an exception. This error is the only one for
    which the command-line client suppresses output.
    """


class NotFoundError(UsageError):
    """
    Raised when a requested resource has not been found. Similar to HTTP status
    404.
    """


class AuthorizationError(UsageError):
    """
    Raised when access to a resource is refused because authentication is required
    and has not been provided. Similar to HTTP status 401.
    """


class PermissionError(UsageError):
    """
    Raised when access to a resource is refused because the user does not have
    necessary permissions. Similar to HTTP status 403.
    """


class LoginPermissionError(ValueError):
    """
    Raised when the login credentials are incorrect.
    """


class DiskQuotaExceededError(ValueError):
    """
    Raised when the disk quota left on the server is less than the bundle size.
    """


class SingularityError(ValueError):
    """
    General purpose singularity error
    """


# Listed in order of most specific to least specific.
http_codes_and_exceptions = [
    (http.client.FORBIDDEN, PermissionError),
    (http.client.UNAUTHORIZED, AuthorizationError),
    (http.client.NOT_FOUND, NotFoundError),
    (http.client.BAD_REQUEST, UsageError),
]


def exception_to_http_error(e):
    """
    Returns the appropriate HTTP error code and message for the given exception.
    """
    for known_code, exception_type in http_codes_and_exceptions:
        if isinstance(e, exception_type):
            return known_code, str(e)
    return http.client.INTERNAL_SERVER_ERROR, str(e)


def http_error_to_exception(code, message):
    """
    Returns the appropriate exception for the given HTTP error code and message.
    """
    for known_code, exception_type in http_codes_and_exceptions:
        if code == known_code:
            return exception_type(message)
    if code >= 400 and code < 500:
        return UsageError(message)
    return Exception(message)


def precondition(condition, message):
    if not condition:
        raise PreconditionViolation(message)


def ensure_str(response):
    """
    Ensure the data type of input response to be string
    :param response: a response in bytes or string
    :return: the input response in string
    """
    if isinstance(response, str):
        return response
    try:
        return response.decode()
    except UnicodeDecodeError:
        return BINARY_PLACEHOLDER


@retry(urllib.error.URLError, tries=2, delay=1, backoff=2)
def urlopen_with_retry(request: urllib.request.Request, timeout: int = URLOPEN_TIMEOUT_SECONDS):
    """
    Makes a request using urlopen with a timeout of URLOPEN_TIMEOUT_SECONDS seconds and retries on failures.
    Retries a maximum of 2 times, with an initial delay of 1 second and
    exponential backoff factor of 2 for subsequent failures (1s and 2s).
    :param request: Can be a url string or a Request object
    :param timeout: Timeout for urlopen in seconds
    :return: the response object
    """
    return urllib.request.urlopen(request, timeout=timeout)


class StorageType(Enum):
    """Possible storage types for bundles.
    When updating this enum, sync it with with the enum in the storage_type column
    in codalab.model.tables and add the appropriate migrations to reflect the column change.
    """

    DISK_STORAGE = "disk"
    AZURE_BLOB_STORAGE = "azure_blob"
    GCS_STORAGE = "gcs"


class StorageURLScheme(Enum):
    """Possible storage URL schemes. URLs for the
    corresponding storage type will begin with the
    scheme specified.
    """

    DISK_STORAGE = ""
    AZURE_BLOB_STORAGE = "azfs://"
    GCS_STORAGE = "gs://"


class StorageFormat(Enum):
    """Possible storage formats for bundles.
    When updating this enum, sync it with with the enum in the storage_format column
    in codalab.model.tables and add the appropriate migrations to reflect the column change.
    """

    # Currently how disk storage stores bundles, just uncompressed.
    UNCOMPRESSED = "uncompressed"

    # Uses ratarmount to construct a single index.sqlite file along with a .tar.gz / .gz
    # version of the bundle.
    COMPRESSED_V1 = "compressed_v1"


@dataclass(frozen=True)
class LinkedBundlePath:
    """A LinkedBundlePath refers to a path that points to the location of a linked bundle within a specific storage location.
    It can either point directly to the bundle, or to a file that is located within that bundle.
    It is constructed by parsing a given bundle link URL by calling parse_bundle_url().

    Attributes:
        storage_type (StorageType): Which storage type is used to store this bundle.

        bundle_path (str): Path to the bundle contents in that particular storage.

        is_archive (bool): Whether this bundle is stored as an indexed archive file (contents.gz / contents.tar.gz + an index.sqlite file. Only done currently by Azure Blob Storage.

        is_archive_dir (bool): Whether this bundle is stored as a contents.tar.gz file (which represents a directory) or
        a contents.gz file (which represents a single file). Only applicable if is_archive is True.

        index_path (str): Path to index.sqlite file that is used to index this bundle's contents. Only applicable if is_archive is True.

        uses_beam (bool): Whether this bundle's storage type requires using Apache Beam to interact with it.

        archive_subpath (str): If is_archive is True, returns the subpath within the archive file for the file that this BundlePath points to.

        bundle_uuid (str): UUID of the bundle that this path refers to.
    """

    storage_type: StorageType
    bundle_path: str
    is_archive: bool
    is_archive_dir: bool
    index_path: str
    uses_beam: bool
    archive_subpath: str
    bundle_uuid: str

    def _get_azure_sas_url(self, path, **kwargs):
        """
        Generates a SAS URL that can be used to read the given blob for one hour.

        Args:
            permission: Different permission granted by SAS token. `r`, `w` or `wr`. `r` for read permission, and `w` for write permission.
        """
        if self.storage_type != StorageType.AZURE_BLOB_STORAGE.value:
            raise ValueError(
                f"SAS URLs can only be retrieved for bundles on Azure Blob Storage. Storage type is: {self.storage_type}."
            )
        blob_name = path.replace(
            f"{StorageURLScheme.AZURE_BLOB_STORAGE.value}{AZURE_BLOB_ACCOUNT_NAME}/{AZURE_BLOB_CONTAINER_NAME}/",
            "",
        )  # for example, "0x9955c356ed2f42e3970bdf647f3358c8/contents.gz"

        permission = kwargs.get("permission", 'r')
        if permission == 'w':
            sas_permission = BlobSasPermissions(write=True)
        elif permission == 'r':
            sas_permission = BlobSasPermissions(read=True)
        elif permission == 'rw':
            sas_permission = BlobSasPermissions(read=True, write=True)
        else:
            raise UsageError("Not supported SAS token permission. Only support `r`/`w`/`rw`.")
        kwargs["permission"] = sas_permission

        sas_token = generate_blob_sas(
            **kwargs,
            account_name=AZURE_BLOB_ACCOUNT_NAME,
            container_name=AZURE_BLOB_CONTAINER_NAME,
            account_key=AZURE_BLOB_ACCOUNT_KEY,
            expiry=datetime.datetime.now() + datetime.timedelta(hours=1),
            blob_name=blob_name,
        )
        return f"{AZURE_BLOB_HTTP_ENDPOINT}/{AZURE_BLOB_CONTAINER_NAME}/{blob_name}?{sas_token}"

    def _get_gcs_signed_url(self, path, **kwargs):
        """Generate GCS signed url that can be used to download the blob for 1 hour."""
        if self.storage_type != StorageType.GCS_STORAGE.value:
            raise ValueError(
                f"Signed URLs can only be retrieved for bundles on Google Cloud Storage. Storage type is: {self.storage_type}."
            )
        client = storage.Client()
        # parse parameters from path, eg: "gs://{bucket_name}/{bundle_uuid}/{contents_file}"
        bucket_name, blob_name = path.replace(f"{StorageURLScheme.GCS_STORAGE.value}", "").split(
            "/", 1
        )
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method=kwargs.get("method", "GET"),  # HTTP method. eg, GET, PUT
            content_type=kwargs.get("request_content_type", None),
            response_disposition=kwargs.get("content_disposition", None),
            response_type=kwargs.get("content_type", None),
        )
        return signed_url

    def bundle_path_bypass_url(self, **kwargs):
        if self.storage_type == StorageType.AZURE_BLOB_STORAGE.value:
            return self._get_azure_sas_url(self.bundle_path, **kwargs)
        elif self.storage_type == StorageType.GCS_STORAGE.value:
            return self._get_gcs_signed_url(self.bundle_path, **kwargs)
        else:
            raise UsageError(f"Does not support current storage type: {self.storage_type}")

    def index_path_bypass_url(self, **kwargs):
        if self.storage_type == StorageType.AZURE_BLOB_STORAGE.value:
            return self._get_azure_sas_url(self.index_path, **kwargs)
        elif self.storage_type == StorageType.GCS_STORAGE.value:
            return self._get_gcs_signed_url(self.index_path, **kwargs)
        else:
            raise UsageError(f"Does not support current storage type: {self.storage_type}")


def parse_linked_bundle_url(url):
    """Parses a linked bundle URL. This bundle URL usually refers to:
        - an archive file on Blob Storage: "azfs://storageclwsdev0/bundles/uuid/contents.tar.gz" (contents.gz for files, contents.tar.gz for directories)
        - a single file that is stored within a subpath of an archive file on Blob Storage: "azfs://storageclwsdev0/bundles/uuid/contents.tar.gz/file1"
        - a container or bucket: "azfs://devstoreaccount1/bundles". Used in "cl store add" command.

        Returns a LinkedBundlePath instance to encode this information.
    """
    if url.startswith(StorageURLScheme.AZURE_BLOB_STORAGE.value) or url.startswith(
        StorageURLScheme.GCS_STORAGE.value
    ):
        uses_beam = True
        if url.startswith(StorageURLScheme.AZURE_BLOB_STORAGE.value):
            storage_type = StorageType.AZURE_BLOB_STORAGE.value
            url = url[len(StorageURLScheme.AZURE_BLOB_STORAGE.value) :]
            try:
                storage_account, container, bundle_uuid, contents_file, *remainder = url.split(
                    "/", 4
                )
                bundle_path = f"{StorageURLScheme.AZURE_BLOB_STORAGE.value}{storage_account}/{container}/{bundle_uuid}/{contents_file}"
            except ValueError:
                # url refers to bucket, e.g. azfs://{storage_account}/{container}
                storage_account, container, *remainder = url.split("/", 2)
                bundle_uuid, contents_file, remainder = None, None, []
                bundle_path = url
        if url.startswith(StorageURLScheme.GCS_STORAGE.value):
            storage_type = StorageType.GCS_STORAGE.value
            url = url[len(StorageURLScheme.GCS_STORAGE.value) :]
            try:
                bucket_name, bundle_uuid, contents_file, *remainder = url.split("/", 3)
                bundle_path = f"{StorageURLScheme.GCS_STORAGE.value}{bucket_name}/{bundle_uuid}/{contents_file}"
            except ValueError:
                # url refers to bucket, e.g. gs://{bucket_name}
                bucket_name, *remainder = url.split("/", 1)
                bundle_uuid, contents_file, remainder = None, None, []
                bundle_path = url
        is_archive = contents_file is not None and (
            contents_file.endswith(".gz") or contents_file.endswith(".tar.gz")
        )
        is_archive_dir = contents_file is not None and contents_file.endswith(".tar.gz")
        index_path = None
        if is_archive:
            # Archive index is stored as an "index.sqlite" file in the same folder as the archive file.
            index_path = re.sub(r'/contents(.tar)?.gz$', '/index.sqlite', bundle_path)
        archive_subpath = remainder[0] if is_archive and len(remainder) else None
    else:
        storage_type = StorageType.DISK_STORAGE.value
        bundle_path = url
        is_archive = False
        is_archive_dir = False
        index_path = None
        uses_beam = False
        archive_subpath = None
        bundle_uuid = None
    return LinkedBundlePath(
        storage_type=storage_type,
        bundle_path=bundle_path,
        is_archive=is_archive,
        is_archive_dir=is_archive_dir,
        index_path=index_path,
        uses_beam=uses_beam,
        archive_subpath=archive_subpath,
        bundle_uuid=bundle_uuid,
    )


class BundleRuntime(Enum):
    """Possible runtimes for jobs. URLs for the
    corresponding storage type will begin with the
    scheme specified.
    """

    DOCKER = "docker"
    SINGULARITY = "singularity"
