# REST API Reference

_version 1.5.7_

This reference and the REST API itself is still under heavy development and is
subject to change at any time. Feedback through our GitHub issues is appreciated!

## Table of Contents
- [Introduction](#introduction)
- [Resource Object Schemas](#resource-object-schemas)
- [API Endpoints](#api-endpoints)
  - [Bundle Actions API](#bundle-actions-api)
  - [Bundle Permissions API](#bundle-permissions-api)
  - [Bundle_Stores API](#bundle_stores-api)
  - [Bundles API](#bundles-api)
  - [CLI API](#cli-api)
  - [Groups API](#groups-api)
  - [OAuth2 API](#oauth2-api)
  - [User API](#user-api)
  - [Users API](#users-api)
  - [Workers API](#workers-api)
  - [Worksheet Interpretation API](#worksheet-interpretation-api)
  - [Worksheet Items API](#worksheet-items-api)
  - [Worksheet Permissions API](#worksheet-permissions-api)
  - [Worksheets API](#worksheets-api)

# Introduction
We use the JSON API v1.0 specification with the Bulk extension.
- http://jsonapi.org/format/
- https://github.com/json-api/json-api/blob/9c7a03dbc37f80f6ca81b16d444c960e96dd7a57/extensions/bulk/index.md

The following specification will not provide the verbose JSON formats of the API requests and responses, as those can be found in the JSON API specification. Instead:
- Each resource type below (worksheets, bundles, etc.) specifies a list of
  attributes with their respective data types and semantics, along with a list
  of relationships.
- Each API call specifies the HTTP request method, the endpoint URI, HTTP
  parameters with their respective data types and semantics, description of the
  API call.

## How we use JSON API

Using the JSON API specification allows us to avoid redesigning the wheel when designing our request and response formats. This also means that we will not specify all the details of the API (for example, Content-Type headers, the fact that POST requests should contain a single resource object, etc.) in this document at this time, while we may choose to continue copying in more details as we go in the design and implementation process. However, since there are many optional features of the JSON API specification, we will document on a best-effort basis the ways in which we will use the specification that are specific to our API, as well as which parts of the specification we use, and which parts we do not.

## Top-level JSON structure

Every JSON request or response will have at its root a JSON object containing either a “data” field or an “error” field, but not both. Thus the presence of an “error” field will unambiguously indicate an error state.

Response documents may also contain a top-level "meta" field, containing additional constructed data that are not strictly resource objects, such as summations in a search query.

Response documents may also contain a top-level "included" field, discussed below.

## Primary Data

The JSON API standard specifies that the “data” field will contain either a [resource object](http://jsonapi.org/format/#document-resource-objects) or an array of resource objects, depending on the nature of the request. More specfically, if the client is fetching a single specific resource (e.g. GET /bundles/0x1d09b495), the “data” field will have a single JSON object at its root. If the client intends to fetch a variable number of resources, then the “data” field will have at its root an array of zero or more JSON objects.

The structure of a JSON response with a single resource object will typically look like this:

```
{
  "data": {
    "type": "bundles",
    "id": "0x1d09b495410249f89dee4465cd21d499",
    "attributes": {
      // ... this bundle's attributes
    },
    "relationships": {
      // ... this bundle's relationships
    }
  }
}
```

Note that we use UUIDs as the "id" of a resource when available (i.e. for worksheets, bundles, and groups) and some other unique key for those resources to which we have not prescribed a UUID scheme.

For each of the resource types available in the Worksheets API, we define the schema for its **attributes**, as well as list what **relationships** each instance may have defined. Relationships are analogous to relationships in relational databases and ORMs—some may be to-one (such as the "owner" of a bundle) and some may be to-many (such as the "permissions" of a bundle).

We will use the following subset of the relationship object schema for our Worksheets API (Orderly schema):

```
object {
  object {
    string related;   // URL to GET the related resource
  } links;
  object {            // used to identify resource in includes
    string type;      // type of the related resource
    string id;        // id of the related resource
  } data?;
}
```

## Query Parameters

The client may provide additional parameters for requests as query parameters in the request URL. Available parameters will be listed under each API route. In general:
- Boolean query parameters are encoded as 1 for "true" and 0 for "false".
- Some query parameters take multiple values, which can be passed by simply listing
  the parameter multiple times in the query, e.g. `GET /bundles?keywords=hello&keywords=world`

## Includes

The client will often want to fetch data for resources related to the primary resource(s) in the same request: for example, client may want to fetch a worksheet along with all of its items, as well as data about the bundles and worksheets referenced in the items.

Currently, most of the API endpoints will include related resources automatically.
For example, fetching a "worksheet" will also include the "bundles" referenced
by the worksheet in the response. These related resource objects will be
included in an array in the top-level "included" field of the response object.

## Non-JSON API Endpoints

The JSON API specification is not all-encompassing, and there are some cases in our API that fall outside of the specification. We will indicate this explicitly where it applies, and provide an alternative schema for the JSON format where necessary.

## Authorization and Authentication

The Bundle Service also serves as an OAuth2 Provider.

All requests to protected resources on the Worksheets API must include a valid
OAuth bearer token in the HTTP headers:

    Authorization: Bearer xxxxtokenxxxx

If the token is expired, does not authorize the application to access the
target resource, or is otherwise invalid, the Bundle Service will respond with
a `401 Unauthorized` or `403 Forbidden` status.

# Resource Object Schemas

## users


Name | Type
--- | ---
`id` | String
`user_name` | String
`first_name` | String
`last_name` | String
`affiliation` | String
`url` | Url
`date_joined` | LocalDateTime
`avatar_id` | String
`has_access` | Boolean
`email` | String
`notifications` | Integer
`time_quota` | Integer
`parallel_run_quota` | Integer
`time_used` | Integer
`disk_quota` | Integer
`disk_used` | Integer
`last_login` | LocalDateTime
`is_verified` | Boolean

## users


Name | Type
--- | ---
`id` | String
`user_name` | String
`first_name` | String
`last_name` | String
`affiliation` | String
`url` | Url
`date_joined` | LocalDateTime
`avatar_id` | String
`has_access` | Boolean
`email` | String
`notifications` | Integer
`time_quota` | Integer
`parallel_run_quota` | Integer
`time_used` | Integer
`disk_quota` | Integer
`disk_used` | Integer
`last_login` | LocalDateTime

## bundle-actions


Name | Type
--- | ---
`id` | Integer
`uuid` | String
`type` | String
`subpath` | String
`string` | String

## BundleDependencySchema


Plain (non-JSONAPI) Marshmallow schema for a single bundle dependency.
Not defining this as a separate resource with Relationships because we only
create a set of dependencies once at bundle creation.


Name | Type
--- | ---
`child_uuid` | String
`child_path` | String
`parent_uuid` | String
`parent_path` | String
`parent_name` | Method
`parent_state` | Method

## bundle_locations


Name | Type
--- | ---
`id` | String
`bundle_store_uuid` | String
`name` | String
`storage_type` | String
`storage_format` | String
`url` | String

## bundle_locations


Name | Type
--- | ---
`id` | String
`bundle_uuid` | String
`bundle_store_uuid` | String

## bundle-permissions


Name | Type
--- | ---
`id` | CompatibleInteger
`bundle` | Relationship([bundles](#bundles))
`group` | Relationship([groups](#groups))
`group_name` | String
`permission` | Integer
`permission_spec` | PermissionSpec

## bundles


Name | Type
--- | ---
`id` | String
`uuid` | String
`bundle_type` | String
`command` | String
`data_hash` | String
`state` | String
`state_details` | String
`owner` | Relationship([users](#users))
`frozen` | DateTime
`is_anonymous` | Boolean
`storage_type` | String
`is_dir` | Boolean
`metadata` | Dict
`dependencies` | [BundleDependencySchema](#BundleDependencySchema)
`children` | Relationship([bundles](#bundles))
`group_permissions` | Relationship([bundle-permissions](#bundle-permissions))
`host_worksheets` | Relationship([worksheets](#worksheets))
`args` | String
`permission` | Integer
`permission_spec` | PermissionSpec

## bundle_stores


Name | Type
--- | ---
`id` | String
`uuid` | String
`owner` | Integer
`name` | String
`storage_type` | String
`storage_format` | String
`url` | String
`authentication` | String
`authentication_env` | String

## groups


Name | Type
--- | ---
`id` | String
`name` | String
`user_defined` | Boolean
`owner` | Relationship([users](#users))
`admins` | Relationship([users](#users))
`members` | Relationship([users](#users))

## users


Name | Type
--- | ---
`id` | String
`user_name` | String
`first_name` | String
`last_name` | String
`affiliation` | String
`url` | Url
`date_joined` | LocalDateTime
`avatar_id` | String
`has_access` | Boolean

## worksheet-items


Name | Type
--- | ---
`id` | CompatibleInteger
`worksheet` | Relationship([worksheets](#worksheets))
`subworksheet` | Relationship([worksheets](#worksheets))
`bundle` | Relationship([bundles](#bundles))
`value` | String
`type` | String
`sort_key` | Integer

## worksheet-permissions


Name | Type
--- | ---
`id` | CompatibleInteger
`worksheet` | Relationship([worksheets](#worksheets))
`group` | Relationship([groups](#groups))
`group_name` | String
`permission` | Integer
`permission_spec` | PermissionSpec

## worksheets


Name | Type
--- | ---
`id` | String
`uuid` | String
`name` | String
`owner` | Relationship([users](#users))
`title` | String
`frozen` | DateTime
`is_anonymous` | Boolean
`date_created` | DateTime
`date_last_modified` | DateTime
`tags` | List
`group_permissions` | Relationship([worksheet-permissions](#worksheet-permissions))
`items` | Relationship([worksheet-items](#worksheet-items))
`last_item_id` | Integer
`permission` | Integer
`permission_spec` | PermissionSpec

&uarr; [Back to Top](#table-of-contents)
# API Endpoints
## Bundle Actions API
### `POST /bundle-actions`

Sends the message to the worker to do the bundle action, and adds the
action string to the bundle metadata.


&uarr; [Back to Top](#table-of-contents)
## Bundle Permissions API
### `POST /bundle-permissions`

Bulk set bundle permissions.

A bundle permission created on a bundle-group pair will replace any
existing permissions on the same bundle-group pair.


&uarr; [Back to Top](#table-of-contents)
## Bundle_Stores API
### `GET /bundle_stores`

Fetch the bundle stores available to the user. No required arguments.

Query parameters:
- `name`: (Optional) name of bundle store. If specified, only query information about the bundle store with given name. If not, return information of all the bundle stores.

Returns a list of bundle stores, each having the following parameters:
- `uuid`: bundle store UUID
- `owner_id`: (integer) owner of bundle store
- `name`: name of bundle store
- `storage_type`: type of storage being used for bundle store (GCP, AWS, etc)
- `storage_format`: the format in which storage is being stored (UNCOMPRESSED, COMPRESSED_V1, etc)
- `url`: a self-referential URL that points to the bundle store.

### `POST /bundle_stores`

Add a bundle store that the user can access.
JSON parameters:
    - `name`: name of bundle store
    - `storage_type`: type of storage being used for bundle store (GCP, AWS, etc)
    - `storage_format`: the format in which storage is being stored (UNCOMPRESSED, COMPRESSED_V1, etc). If unspecified, an optimal default will be set.
    - `url`: a self-referential URL that points to the bundle store.
    - `authentication`: key for authentication that the bundle store uses.
Returns the data of the created bundle store.

### `GET /bundle_stores/<uuid:re:0x[0-9a-f]{32}>`

Fetch the bundle store corresponding to the specified uuid.

Returns a single bundle store, with the following parameters:
- `uuid`: bundle store UUID
- `owner_id`: owner of bundle store
- `name`: name of bundle store
- `storage_type`: type of storage being used for bundle store (GCP, AWS, etc)
- `storage_format`: the format in which storage is being stored (UNCOMPRESSED, COMPRESSED_V1, etc)
- `url`: a self-referential URL that points to the bundle store.

### `DELETE /bundle_stores`

Delete the specified bundle stores.


&uarr; [Back to Top](#table-of-contents)
## Bundles API
### `GET /bundles/<uuid:re:0x[0-9a-f]{32}>`

Fetch bundle by UUID.

Query parameters:

 - `include_display_metadata`: `1` to include additional metadata helpful
   for displaying the bundle info, `0` to omit them. Default is `0`.
 - `include`: comma-separated list of related resources to include, such as "owner"

### `GET /bundles`

Fetch bundles in the following two ways:
1. By bundle `specs` OR search `keywords` . Behavior is undefined
when both `specs` and `keywords` are provided.

Query parameters:

 - `worksheet`: UUID of the base worksheet. Required when fetching by specs.
 - `specs`: Bundle spec of bundle to fetch. May be provided multiples times
    to fetch multiple bundle specs. A bundle spec is either:
    1. a UUID (8 or 32 hex characters with a preceding '0x')
    2. a bundle name referring to the last bundle with that name on the
       given base worksheet
    3. or a reverse index of the form `^N` referring to the Nth-to-last
       bundle on the given base worksheet.
 - `keywords`: Search keyword. May be provided multiple times for multiple
    keywords. Bare keywords match the names and descriptions of bundles.
    Examples of other special keyword forms:
    - `name=<name>            ` : More targeted search of using metadata fields.
    - `size=.sort             ` : Sort by a particular field.
    - `size=.sort-            ` : Sort by a particular field in reverse.
    - `size=.sum              ` : Compute total of a particular field.
    - `.mine                  ` : Match only bundles I own.
    - `.floating              ` : Match bundles that aren't on any worksheet.
    - `.count                 ` : Count the number of bundles.
    - `.limit=10              ` : Limit the number of results to the top 10.
 - `include_display_metadata`: `1` to include additional metadata helpful
   for displaying the bundle info, `0` to omit them. Default is `0`.
 - `include`: comma-separated list of related resources to include, such as "owner"

When aggregation keywords such as `.count` are used, the resulting value
is returned as:
```
{
    "meta": {
        "results": <value>
    }
}
```
2. By bundle `command` and/or `dependencies` (for `--memoized` option in cl [run/mimic] command).
When `dependencies` is not defined, the searching result will include bundles that match with command only.

Query parameters:
 - `command`      : the command of a bundle in string
 - `dependencies` : the dependencies of a bundle in the format of
                    '[{"child_path":key1, "parent_uuid":UUID1},
                    {"child_path":key2, "parent_uuid":UUID2}]'
    1. a UUID should be in the format of 32 hex characters with a preceding '0x' (partial UUID is not allowed).
    2. the key should be able to uniquely identify a (child_path, parent_uuid) pair in the list.
The returning result will be aggregated in the same way as 1.

### `POST /bundles`

Bulk create bundles.

Query parameters:
- `worksheet`: UUID of the parent worksheet of the new bundle, add to
  this worksheet if not detached or shadowing another bundle. The new
  bundle also inherits permissions from this worksheet.
- `shadow`: UUID of the bundle to "shadow" (the new bundle will be added
  as an item immediately after this bundle in its parent worksheet).
- `detached`: 1 if should not add new bundle to any worksheet,
  so the bundle does not have a hosted worksheet.
  This is set to 1, for example, if the user is uploading their avatar as a bundle.
  or 0 otherwise. Default is 0.
- `wait_for_upload`: 1 if the bundle state should be initialized to
  "uploading" regardless of the bundle type, or 0 otherwise. Used when
  copying bundles from another CodaLab instance, this prevents these new
  bundles from being executed by the BundleManager. Default is 0.

### `PATCH /bundles`

Bulk update bundles.

### `DELETE /bundles`

Delete the bundles specified.

Query parameters:
 - `force`: 1 to allow deletion of bundles that have descendants or that
   appear across multiple worksheets, or 0 to throw an error if any of the
   specified bundles have multiple references. Default is 0.
 - `recursive`: 1 to remove all bundles downstream too, or 0 otherwise.
   Default is 0.
 - `data-only`: 1 to only remove contents of the bundle(s) from the bundle
   store and leave the bundle metadata intact, or 0 to remove both the
   bundle contents and the bundle metadata. Default is 0.
 - `dry-run`: 1 to just return list of bundles that would be deleted with
   the given parameters without actually deleting them, or 0 to perform
   the deletion. Default is 0.

### `GET /bundles/locations`

Fetch locations of bundles.

Query parameters:
- `uuids`: List of bundle UUID's to get the locations for

### `GET /bundles/<bundle_uuid:re:0x[0-9a-f]{32}>/locations/`

Returns a list of BundleLocations associated with the given bundle.

Query parameters:
- `bundle_uuid`: Bundle UUID to get the locations for

### `POST /bundles/<bundle_uuid:re:0x[0-9a-f]{32}>/locations/`

Adds a new BundleLocation to a bundle. If need to generate sas token, generate Azure SAS token and connection string. Request body must contain the fields in BundleLocationSchema.

Query parameters:
- `need_bypass`: (Optional) Bool. If true, if will return SAS token (for Azure) or signed url (for GCS) to bypass server upload.
- `is_dir`: (Optional) Bool. Whether the uploaded file is directory.

### `GET /bundles/<bundle_uuid:re:%s>/locations/<bundle_store_uuid:re:%s>/`

Get info about a specific BundleLocation.

Query parameters:
- `bundle_uuid`: Bundle UUID to get the location for
- `bundle_store_uuid`: Bundle Store UUID to get the location for

### `POST /bundles/<bundle_uuid:re:0x[0-9a-f]{32}>/state`

Updates a bundle state. Used to finalize a bundle's upload status
after it is uploaded by the client directly to the bundle store,
such as uploading to blob storage and bypassing the server.

Query parameters:
- `success`: The state of upload.
- `state_on_success`: (Optional) String. New bundle state if success
- `state_on_failure`: (Optional) String. Bundle UUID corresponding to the new location
- `error_msg`: (Optional) String. Error message if upload fails.

### `GET /bundles/<uuid:re:0x[0-9a-f]{32}>/contents/info/<path:path>`

Fetch metadata of the bundle contents or a subpath within the bundle.

Query parameters:
- `depth`: recursively fetch subdirectory info up to this depth.
  Default is 0.

Response format:
```
{
  "data": {
      "name": "<name of file or directory>",
      "link": "<string representing target if file is a symbolic link>",
      "type": "<file|directory|link>",
      "size": <size of file in bytes>,
      "perm": <unix permission integer>,
      "contents": [
          {
            "name": ...,
            <each file of directory represented recursively with the same schema>
          },
          ...
      ]
  }
}
```

### `GET /bundles/<uuid:re:0x[0-9a-f]{32}>/contents/info/`

Fetch metadata of the bundle contents or a subpath within the bundle.

Query parameters:
- `depth`: recursively fetch subdirectory info up to this depth.
  Default is 0.

Response format:
```
{
  "data": {
      "name": "<name of file or directory>",
      "link": "<string representing target if file is a symbolic link>",
      "type": "<file|directory|link>",
      "size": <size of file in bytes>,
      "perm": <unix permission integer>,
      "contents": [
          {
            "name": ...,
            <each file of directory represented recursively with the same schema>
          },
          ...
      ]
  }
}
```

### `PUT /bundles/<uuid:re:0x[0-9a-f]{32}>/netcat/<port:int>/`

Send a raw bytestring into the specified port of the running bundle with uuid.
Return the response from this bundle.

### `PATCH /bundles/<uuid:re:0x[0-9a-f]{32}>/netcurl/<port:int>/<path:re:.*>`

Forward an HTTP request into the specified port of the running bundle with uuid.
Return the HTTP response from this bundle.

### `GET /bundles/<uuid:re:0x[0-9a-f]{32}>/netcurl/<port:int>/<path:re:.*>`

Forward an HTTP request into the specified port of the running bundle with uuid.
Return the HTTP response from this bundle.

### `DELETE /bundles/<uuid:re:0x[0-9a-f]{32}>/netcurl/<port:int>/<path:re:.*>`

Forward an HTTP request into the specified port of the running bundle with uuid.
Return the HTTP response from this bundle.

### `PUT /bundles/<uuid:re:0x[0-9a-f]{32}>/netcurl/<port:int>/<path:re:.*>`

Forward an HTTP request into the specified port of the running bundle with uuid.
Return the HTTP response from this bundle.

### `POST /bundles/<uuid:re:0x[0-9a-f]{32}>/netcurl/<port:int>/<path:re:.*>`

Forward an HTTP request into the specified port of the running bundle with uuid.
Return the HTTP response from this bundle.

### `GET /bundles/<uuid:re:0x[0-9a-f]{32}>/contents/blob/<path:path>`

API to download the contents of a bundle or a subpath within a bundle.

For directories, this method always returns a tarred and gzipped archive of
the directory.

For files, if the request has an Accept-Encoding header containing gzip,
then the returned file is gzipped. Otherwise, the file is returned as-is.

HTTP Request headers:
- `Range: bytes=<start>-<end>`: fetch bytes from the range
  `[<start>, <end>)`.
- `Accept-Encoding: <encoding>`: indicate that the client can accept
  encoding `<encoding>`. Currently only `gzip` encoding is supported.

Query parameters:
- `head`: number of lines to fetch from the beginning of the file.
  Default is 0, meaning to fetch the entire file.
- `tail`: number of lines to fetch from the end of the file.
  Default is 0, meaning to fetch the entire file.
- `max_line_length`: maximum number of characters to fetch from each line,
  if either `head` or `tail` is specified. Default is 128.
- `support_redirect`: Set to 1 if the client supports bypassing the server
  and redirecting to another URL (such as Blob Storage). If so, the Target-Type and
  X-CodaLab-Target-Size headers will not be present in the response.

  If this endpoint is called from a web browser (`Referer` header is set), this parameter
  defaults to 1. Otherwise, it defaults to 0, meant for compatibility
  with older clients / CLI versions that depend on the Target-Type and
  X-CodaLab-Target-Size headers. In a future release, this parameter will always
  be set to 1.

HTTP Response headers (for single-file targets):
- `Content-Disposition: inline; filename=<bundle name or target filename>`
- `Content-Type: <guess of mimetype based on file extension>`
- `Content-Encoding: [gzip|identity]`
- `Target-Type: file`
- `X-CodaLab-Target-Size: <size of the target>`

HTTP Response headers (for directories):
- `Content-Disposition: attachment; filename=<bundle or directory name>.tar.gz`
- `Content-Type: application/gzip`
- `Content-Encoding: identity`
- `Target-Type: directory`
- `X-CodaLab-Target-Size: <size of the target>`

Note that X-CodaLab-Target-Size is the uncompressed version of the target size. This means that it will
be equivalent to the downloaded file if from a single-file target, but will be the size of the uncompressed
archive, not the compressed archive, if from a directory target.

### `GET /bundles/<uuid:re:0x[0-9a-f]{32}>/contents/blob/`

API to download the contents of a bundle or a subpath within a bundle.

For directories, this method always returns a tarred and gzipped archive of
the directory.

For files, if the request has an Accept-Encoding header containing gzip,
then the returned file is gzipped. Otherwise, the file is returned as-is.

HTTP Request headers:
- `Range: bytes=<start>-<end>`: fetch bytes from the range
  `[<start>, <end>)`.
- `Accept-Encoding: <encoding>`: indicate that the client can accept
  encoding `<encoding>`. Currently only `gzip` encoding is supported.

Query parameters:
- `head`: number of lines to fetch from the beginning of the file.
  Default is 0, meaning to fetch the entire file.
- `tail`: number of lines to fetch from the end of the file.
  Default is 0, meaning to fetch the entire file.
- `max_line_length`: maximum number of characters to fetch from each line,
  if either `head` or `tail` is specified. Default is 128.
- `support_redirect`: Set to 1 if the client supports bypassing the server
  and redirecting to another URL (such as Blob Storage). If so, the Target-Type and
  X-CodaLab-Target-Size headers will not be present in the response.

  If this endpoint is called from a web browser (`Referer` header is set), this parameter
  defaults to 1. Otherwise, it defaults to 0, meant for compatibility
  with older clients / CLI versions that depend on the Target-Type and
  X-CodaLab-Target-Size headers. In a future release, this parameter will always
  be set to 1.

HTTP Response headers (for single-file targets):
- `Content-Disposition: inline; filename=<bundle name or target filename>`
- `Content-Type: <guess of mimetype based on file extension>`
- `Content-Encoding: [gzip|identity]`
- `Target-Type: file`
- `X-CodaLab-Target-Size: <size of the target>`

HTTP Response headers (for directories):
- `Content-Disposition: attachment; filename=<bundle or directory name>.tar.gz`
- `Content-Type: application/gzip`
- `Content-Encoding: identity`
- `Target-Type: directory`
- `X-CodaLab-Target-Size: <size of the target>`

Note that X-CodaLab-Target-Size is the uncompressed version of the target size. This means that it will
be equivalent to the downloaded file if from a single-file target, but will be the size of the uncompressed
archive, not the compressed archive, if from a directory target.

### `PUT /bundles/<uuid:re:0x[0-9a-f]{32}>/contents/blob/`

Update the contents of the given running or uploading bundle.

Query parameters:
- `urls`: (optional) URL from which to fetch data to fill the bundle;
  using this option will ignore any uploaded file data. Only supports one URL.
- `git`: (optional) 1 if URL should be interpreted as git repos to clone
  or 0 otherwise, default is 0.
- `filename`: (optional) filename of the uploaded file, used to indicate
  whether or not it is an archive, default is 'contents'
- `unpack`: (optional) 1 if the uploaded file should be unpacked if it is
  an archive, or 0 otherwise, default is 1
- `finalize_on_failure`: (optional) 1 if bundle state should be set
  to 'failed' in the case of a failure during upload, or 0 if the bundle
  state should not change on failure. Default is 0.
- `finalize_on_success`: (optional) 1 if bundle state should be set
  to 'state_on_success' when the upload finishes successfully. Default is
  True
- `state_on_success`: (optional) Update the bundle state to this state if
  the upload completes successfully. Must be either 'ready' or 'failed'.
  Default is 'ready'.
- `use_azure_blob_beta`: (optional) Use Azure Blob Storage to store the bundle.
  Default is False. If CODALAB_ALWAYS_USE_AZURE_BLOB_BETA is set, this parameter
  is disregarded, as Azure Blob Storage will always be used.
- `store`: (optional) The name of the bundle store where the bundle should be uploaded to.
  If unspecified, the CLI will pick the optimal available bundle store.


&uarr; [Back to Top](#table-of-contents)
## CLI API
### `POST /cli/command`

JSON request body:
```
{
    "worksheet_uuid": "0xea72f9b6aa754636a6657ff2b5e005b0",
    "command": "cl run :main.py 'python main.py'",
    "autocomplete": false
}
```

JSON response body:
```
{
    "structured_result": { ... },
    "output": "..."
}
```


&uarr; [Back to Top](#table-of-contents)
## Groups API
### `GET /groups/<group_spec>`
Fetch a single group.
### `GET /groups`
Fetch list of groups readable by the authenticated user.
### `DELETE /groups`
Delete groups.
### `POST /groups`
Create a group.
### `POST /groups/<group_spec>/relationships/admins`
### `POST /groups/<group_spec>/relationships/members`
### `DELETE /groups/<group_spec>/relationships/members`
### `DELETE /groups/<group_spec>/relationships/admins`

&uarr; [Back to Top](#table-of-contents)
## OAuth2 API
### `GET /oauth2/authorize`

'authorize' endpoint for OAuth2 authorization code flow.

### `POST /oauth2/authorize`

'authorize' endpoint for OAuth2 authorization code flow.

### `POST /oauth2/token`

OAuth2 token endpoint.

Access token request:

    grant_type
        REQUIRED.  Value MUST be set to "password".

    username
        REQUIRED.  The resource owner username.

    password
        REQUIRED.  The resource owner password.

    scope
        OPTIONAL.  The scope of the access request. (UNUSED)

Example successful response:

    HTTP/1.1 200 OK
    Content-Type: application/json;charset=UTF-8
    Cache-Control: no-store
    Pragma: no-cache

    {
      "access_token":"2YotnFZFEjr1zCsicMWpAA",
      "token_type":"example",
      "expires_in":3600,
      "refresh_token":"tGzv3JOkF0XG5Qx2TlKWIA",
      "example_parameter":"example_value"
    }

### `POST /oauth2/revoke`
Provide secure services using OAuth2.
    The server should provide an authorize handler and a token handler,

    But before the handlers are implemented, the server should provide
    some getters for the validation.
    There are two usage modes. One is binding the Bottle app instance:

        app = Bottle()
        oauth = OAuth2Provider(app)

    The second possibility is to bind the Bottle app later:

        oauth = OAuth2Provider()

        def create_app():
            app = Bottle()
            oauth.app = app
            return app

    Configure :meth:`tokengetter` and :meth:`tokensetter` to get and
    set tokens. Configure :meth:`grantgetter` and :meth:`grantsetter`
    to get and set grant tokens. Configure :meth:`clientgetter` to
    get the client.

    Configure :meth:`usergetter` if you need password credential
    authorization.

    With everything ready, implement the authorization workflow:

        * :meth:`authorize_handler` for consumer to confirm the grant
        * :meth:`token_handler` for client to exchange access token

    And now you can protect the resource with scopes::

        @app.route('/api/user')
        @oauth.check_oauth('email', 'username')
        def user():
            return jsonify(request.user)

### `GET /oauth2/errors`

&uarr; [Back to Top](#table-of-contents)
## User API
### `GET /user`
Fetch authenticated user.
### `PATCH /user`
Update one or multiple fields of the authenticated user.

&uarr; [Back to Top](#table-of-contents)
## Users API
### `GET /users/<user_spec>`
Fetch a single user.
### `DELETE /users`
Fetch user ids
### `GET /users`

Fetch list of users, filterable by username and email.

Takes the following query parameters:
    filter[user_name]=name1,name2,...
    filter[email]=email1,email2,...

Query parameters:

- `keywords`: Search keyword. May be provided multiple times for multiple
keywords.
Examples of other special keyword forms:
- `name=<name>            ` : More targeted search of using metadata fields.
- `date_joined=.sort             ` : Sort by a particular field.
- `date_joined=.sort-            ` : Sort by a particular field in reverse.
- `.count                 ` : Count the number of users.
- `.limit=10              ` : Limit the number of results to the top 10.

### `PATCH /users`

Update arbitrary users.

This operation is reserved for the root user. Other users can update their
information through the /user "authenticated user" API.
Follows the bulk-update convention in the CodaLab API, but currently only
allows one update at a time.


&uarr; [Back to Top](#table-of-contents)
## Workers API
### `POST /workers/<worker_id>/checkin`

Checks in with the bundle service, storing information about the worker.
Waits for a message for the worker for WAIT_TIME_SECS seconds. Returns the
message or None if there isn't one.

### `POST /workers/<worker_id>/reply/<socket_id:int>`

Replies with a single JSON message to the given socket ID.

### `POST /workers/<worker_id>/reply_data/<socket_id:int>`

Replies with a stream of data to the given socket ID. This reply mechanism
works through 2 messages sent by this method: the first message is a header
message containing metadata. The second message streams the actual data in.

The contents of the first message are parsed from the header_message query
parameter, which should be in JSON format.

The contents of the second message go in the body of the HTTP request.

### `POST /workers/<worker_id>/start_bundle/<uuid:re:0x[0-9a-f]{32}>`

Checks whether the bundle is still assigned to run on the worker with the
given worker_id. If so, reports that it's starting to run and returns True.
Otherwise, returns False, meaning the worker shouldn't run the bundle.

### `GET /workers/info`

&uarr; [Back to Top](#table-of-contents)
## Worksheet Interpretation API
### `POST /interpret/search`

Returns worksheet items given a search query for bundles.

JSON request body:
```
{
    "keywords": [ list of search keywords ],
    "schemas": {
        schema_key: [ list of schema columns ],
        ...
    },
    "display": [ display args ]
}
```

### `POST /interpret/wsearch`

Returns worksheets information given a search query for worksheets.

JSON request body:
```
{
    "keywords": [ list of search keywords ]
}
```

Response body:
```
{
    "response": [
        {id: 6,
        uuid: "0x5505f540936f4d0d919f3186141192b0",
        name: "codalab-a",
        title: "CodaLab Dashboard",
        frozen: null,
        owner_id: "0"
        owner_name: "codalab"
        group_permissions: {
            id: 8,
            group_uuid: "0x41e95d8592de417cbb726085d6986137",
            group_name: "public",
            permission: 1}
        }
        ...
    ]
}
```

### `POST /interpret/file-genpaths`

Interpret a file genpath.

JSON request body:
```
{
    "queries": [
        {
            "bundle_uuid": "<uuid>",
            "genpath": "<genpath>",
            "post": "<postprocessor spec>",
        },
        ...
    ]
}
```

Response body:
```
{
    "data": [
        "<resolved file genpath data>",
        ...
    ]
}
```

### `POST /interpret/genpath-table-contents`

Takes a table and fills in unresolved genpath specifications.

JSON request body:
```
{
    "contents": [
        {
            col1: "<resolved string>",
            col2: (bundle_uuid, genpath, post),
            ...
        },
        ...
    ]
}
```

JSON response body:
```
{
    "contents": [
        {
            col1: "<resolved string>",
            col2: "<resolved string>",
            ...
        },
        ...
    ]
}
```

### `GET /interpret/worksheet/<uuid:re:0x[0-9a-f]{32}>`

Return information about a worksheet. Calls
- get_worksheet_info: get basic info
- resolve_interpreted_items: get more information about a worksheet.
In the future, for large worksheets, might want to break this up so
that we can render something basic.
Return:
    worksheet_info dict{}:
        key:[value_type] <description>
        blocks:[list]
                Resolved worksheet blocks from raw_items.
                    Bundles will be grouped into table block items,
                    text items might be grouped into one markdown block etc.
        source:[list] source lines
        raw_to_block:[list]
                        Raw_items to its block index pair.
                            For example, assume the first resolved block item is a bundle table that has 2 rows,
                            then the 2nd element in the list would be [0, 1]
                            [0, 1]: 0 means the item belongs to the first block,
                                    1 means the item is the second item of the block (2nd bundle in our example)
                            NOTE: Used for setting focus on frontend
        block_to_raw:[dict]
                        Maps the blocks (table, markdown, records) to their corresponding source line indices,
                        it's mostly a reverse mapping of raw_to_block, by mostly: raw_to_block has some bug,
                        please refer to worksheet_utils flush_bundles function.
                        This can be used to index the source on the frontend
                        Example:
                        [0, 0]: 0
                        [0, 1]: 1
                        [1, 0]: 9
                        This means the first blocks' first item corresponds to the first line in source,
                        the second item corresponds to the second line in source
                        The second block corresponds the 10th line in source.
                        2-8 can be skipped for multiple reasons: blank lines, comments, schema lines etc.
                            NOTE: Used for setting focus on frontend
This endpoint can be called with &brief=1 in order to give an abbreviated version,
which does not resolve searches or wsearches.
To return an interpreted worksheet that only resolves a particular search/wsearch,
pass in the search query to the "directive" argument. The value for this argument
must be a search/wsearch query -- for example, &directive=search 0x .limit=100


&uarr; [Back to Top](#table-of-contents)
## Worksheet Items API
### `POST /worksheet-items`

Bulk add worksheet items.

|replace| - Replace existing items in host worksheets. Default is False.


&uarr; [Back to Top](#table-of-contents)
## Worksheet Permissions API
### `POST /worksheet-permissions`

Bulk set worksheet permissions.


&uarr; [Back to Top](#table-of-contents)
## Worksheets API
### `GET /worksheets/<uuid:re:0x[0-9a-f]{32}>`

Fetch a single worksheet by UUID.

Query parameters:

 - `include`: comma-separated list of related resources to include, such as "owner"

### `GET /worksheets`

Fetch worksheets by worksheet specs (names) OR search keywords.

Query parameters:

 - `include`: comma-separated list of related resources to include, such as "owner"

### `POST /worksheets`
### `POST /worksheets/<uuid:re:0x[0-9a-f]{32}>/raw`

Request body contains the raw lines of the worksheet.

### `PUT /worksheets/<uuid:re:0x[0-9a-f]{32}>/raw`

Request body contains the raw lines of the worksheet.

### `PATCH /worksheets`

Bulk update worksheets metadata.

### `DELETE /worksheets`

Delete the bundles specified.
If |force|, allow deletion of bundles that have descendants or that appear across multiple worksheets.
If |recursive|, add all bundles downstream too.
If |data-only|, only remove from the bundle store, not the bundle metadata.
If |dry-run|, just return list of bundles that would be deleted, but do not actually delete.

### `POST /worksheets/<worksheet_uuid:re:0x[0-9a-f]{32}>/add-items`

Replace worksheet items with 'ids' with new 'items'.
The new items will be inserted after the after_sort_key

### `GET /worksheets/sample/`

Get worksheets to display on the front page.
Keep only |worksheet_uuids|.

### `GET /worksheets/`

&uarr; [Back to Top](#table-of-contents)
