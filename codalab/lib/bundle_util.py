import copy
import json

from codalab.bundles import get_bundle_subclass

# JsonApiClient is used to explain the first argument of mimic_bundles, so keep it
from codalab.client.json_api_client import JsonApiClient, JsonApiRelationship  # NOQA: F401
from codalab.common import PermissionError, UsageError
from codalab.lib import worksheet_util
from codalab.worker.bundle_state import BundleInfo, State


def bundle_to_bundle_info(model, bundle):
    """
    Helper: Convert bundle to bundle_info.
    """
    # See tables.py
    dependencies = [dep.to_dict() for dep in bundle.dependencies]
    if dependencies:
        dep_names = model.get_bundle_names([dep['parent_uuid'] for dep in dependencies])
        for dep in dependencies:
            dep['parent_name'] = dep_names.get(dep['parent_uuid'])

    info = BundleInfo(
        bundle.uuid,
        bundle.bundle_type,
        bundle.owner_id,
        bundle.command,
        bundle.data_hash,
        bundle.state,
        bundle.frozen,
        bundle.is_anonymous,
        bundle.metadata.to_dict(),
        dependencies,
        '',
    ).as_dict

    # For some reason computing the args requires the rest of the dict
    # This is ugly but we have to deal with it for the time being
    info['args'] = worksheet_util.interpret_genpath(info, 'args')
    return info


def mimic_bundles(
    client,
    old_inputs,
    old_output,
    new_inputs,
    new_output_name,
    worksheet_uuid,
    depth,
    shadow,
    dry_run,
    metadata_override=None,
    skip_prelude=False,
    memoize=False,
):
    """
    :param JsonApiClient client: client
    :param old_inputs: list of bundle uuids
    :param old_output: bundle uuid that we produced
    :param new_inputs: list of bundle uuids that are analogous to old_inputs
    :param new_output_name: name of the bundle to create to be analogous to old_output (possibly None)
    :param worksheet_uuid: add newly created bundles to this worksheet
    :param depth: how far to do a BFS up from old_output.
    :param shadow: whether to add the new inputs right after all occurrences of the old inputs in worksheets.
    :param dry_run: return plan without executing anything if True.
    :param skip_prelude: don't include preludes in mimicked items if True.
    :param metadata_override: new metadata fields replace old ones in the newly mimicked bundles.
    """
    if metadata_override is None:
        metadata_override = {}

    # Build the graph (get all the infos).
    # If old_output is given, look at ancestors of old_output until we
    # reached some depth.  If it's not given, we first get all the
    # descendants first, and then get their ancestors.
    if old_output:
        infos = client.fetch('bundles', params={'specs': old_output})
        assert isinstance(infos, list)
    else:
        # Fetch bundles specified in `old_inputs` and their descendants
        # down by `depth` levesl
        infos = client.fetch('bundles', params={'specs': old_inputs, 'depth': depth})
    infos = {b['uuid']: b for b in infos}  # uuid -> bundle info

    def get_self_and_ancestors(bundle_uuids):
        # Traverse up ancestors by at most `depth` levels and returns
        # the set of all bundles visited, as well as updating the `info`
        # dictionary along the way.
        result = bundle_uuids
        visited = set()
        for _ in range(depth):
            next_bundle_uuids = []
            for bundle_uuid in bundle_uuids:
                if bundle_uuid in visited:
                    continue

                # Add to infos if not there yet
                if bundle_uuid not in infos:
                    infos[bundle_uuid] = client.fetch('bundles', bundle_uuid)

                # Append all of the parents to the next batch of bundles to look at
                info = infos[bundle_uuid]
                for dep in info['dependencies']:
                    parent_uuid = dep['parent_uuid']
                    if parent_uuid not in infos:
                        next_bundle_uuids.append(parent_uuid)

                # Mark this bundle as visited
                visited.add(bundle_uuid)

            # Prepend to the running list of all bundles
            result = next_bundle_uuids + result

            # Swap in the next batch of bundles for next iteration
            bundle_uuids = next_bundle_uuids
        return result

    all_bundle_uuids = get_self_and_ancestors(list(infos.keys()))

    # Now go recursively create the bundles.
    old_to_new = {}  # old_uuid -> new_uuid
    downstream = (
        set()
    )  # old_uuid -> whether we're downstream of an input (and actually needs to be mapped onto a new uuid)
    created_uuids = set()  # set of uuids which were newly created
    plan = []  # sequence of (old, new) bundle infos to make
    for old, new in zip(old_inputs, new_inputs):
        old_to_new[old] = new
        downstream.add(old)

    # Return corresponding new_bundle_uuid
    def recurse(old_bundle_uuid):
        if old_bundle_uuid in old_to_new:
            return old_to_new[old_bundle_uuid]

        # Don't have any more information (because we probably hit the maximum depth)
        if old_bundle_uuid not in infos:
            return old_bundle_uuid

        # Get information about the old bundle.
        old_info = infos[old_bundle_uuid]
        new_dependencies = [
            {
                'parent_uuid': recurse(dep['parent_uuid']),
                'parent_path': dep['parent_path'],
                'child_uuid': dep[
                    'child_uuid'
                ],  # This is just a placeholder to do the equality test
                'child_path': dep['child_path'],
            }
            for dep in old_info['dependencies']
        ]
        # If there are no inputs or if we're downstream of any inputs, we need to make a new bundle.
        lone_output = len(old_inputs) == 0 and old_bundle_uuid == old_output
        downstream_of_inputs = any(
            dep['parent_uuid'] in downstream for dep in old_info['dependencies']
        )
        if lone_output or downstream_of_inputs:
            # Now create a new bundle that mimics the old bundle.
            new_info = copy.deepcopy(old_info)

            # Make sure that new uuids are generated
            new_info.pop('uuid', None)
            new_info.pop('id', None)

            # Remove state_details, as this field is not stored in the db.
            new_info.pop('state_details')

            # Only change the name if the output name is supplied.
            new_metadata = new_info['metadata']
            if new_output_name:
                if old_bundle_uuid == old_output:
                    new_metadata['name'] = new_output_name
                else:
                    # Just make up a name heuristically
                    new_metadata['name'] = new_output_name + '-' + old_info['metadata']['name']

            # By default, the mimic bundle uses whatever image the old bundle uses
            # Preferably it uses the SHA256 image digest, but it may simply copy request_docker_image
            # if it is not present
            if new_info['bundle_type'] == 'run' and new_metadata.get('docker_image', ''):
                # Put docker_image in requested_docker_image if it is present and this is a run bundle
                new_metadata['request_docker_image'] = new_metadata['docker_image']

            cls = get_bundle_subclass(new_info['bundle_type'])
            for spec in cls.METADATA_SPECS:
                # Remove automatically generated keys
                if spec.generated and spec.key in new_metadata:
                    del new_metadata[spec.key]
                # Override original metadata keys
                if spec.key in metadata_override:
                    new_metadata[spec.key] = metadata_override[spec.key]

            # Set up info dict
            new_info['metadata'] = new_metadata
            new_info['dependencies'] = new_dependencies

            # Fetch the memoized bundle if the memoize option is set to be True
            if memoize:
                # A list of matched uuids in the order they were created.
                memoized_bundles = client.fetch(
                    'bundles',
                    params={
                        'command': old_info['command'],
                        'dependencies': json.dumps(
                            [
                                {'child_path': dep['child_path'], 'parent_uuid': dep['parent_uuid']}
                                for dep in new_dependencies
                            ]
                        ),
                    },
                )

            if dry_run:
                new_info['uuid'] = None
            elif memoize and len(memoized_bundles) > 0:
                new_info = memoized_bundles[-1]
            else:
                if new_info['bundle_type'] not in ('make', 'run'):
                    raise UsageError(
                        'Can\'t mimic %s since it is not make or run' % old_bundle_uuid
                    )

                # Create the new bundle, requesting to shadow the old
                # bundle in its worksheet if shadow is specified, otherwise
                # leave the bundle detached, to be added later below.
                params = {}
                params['worksheet'] = worksheet_uuid
                if shadow:
                    params['shadow'] = old_info['uuid']
                else:
                    params['detached'] = True
                new_info = client.create('bundles', new_info, params=params)

            new_bundle_uuid = new_info['uuid']
            plan.append((old_info, new_info))
            downstream.add(old_bundle_uuid)
            created_uuids.add(new_bundle_uuid)
        else:
            new_bundle_uuid = old_bundle_uuid

        old_to_new[old_bundle_uuid] = new_bundle_uuid  # Cache it
        return new_bundle_uuid

    if old_output:
        recurse(old_output)
    else:
        # Don't have a particular output we're targetting, so just create
        # new versions of all the uuids.
        for uuid in all_bundle_uuids:
            recurse(uuid)

    # Add to worksheet
    if not dry_run and not shadow:

        # A prelude of a bundle on a worksheet is the set of items (markup, directives, etc.)
        # that occur immediately before it, until the last preceding newline.
        # Let W be the first worksheet containing the old_inputs[0].
        # Add all items on that worksheet that appear in old_to_new along with their preludes.
        # For items not on this worksheet, add them at the end (instead of making them floating).
        if old_output:
            anchor_uuid = old_output
        elif len(old_inputs) > 0:
            anchor_uuid = old_inputs[0]

        # Find worksheets that contain the anchor bundle
        host_worksheets = client.fetch('worksheets', params={'keywords': 'bundle=' + anchor_uuid})
        host_worksheet_uuids = [hw['id'] for hw in host_worksheets]
        new_bundle_uuids_added = set()

        if len(host_worksheet_uuids) > 0:
            # Choose a single worksheet.
            if worksheet_uuid in host_worksheet_uuids:
                # If current worksheet is one of them, favor that one.
                host_worksheet_uuid = worksheet_uuid
            else:
                # Choose an arbitrary one (in the future, have a better way of canonicalizing).
                host_worksheet_uuid = host_worksheet_uuids[0]

            # Fetch the worksheet
            worksheet_info = client.fetch(
                'worksheets', host_worksheet_uuid, params={'include': ['items', 'items.bundle']}
            )

            prelude_items = []  # The prelude that we're building up
            for item in worksheet_info['items']:

                if item['type'] == worksheet_util.TYPE_BUNDLE:
                    old_bundle_uuid = item['bundle']['id']
                    if old_bundle_uuid in old_to_new:
                        # Flush the prelude gathered so far.
                        new_bundle_uuid = old_to_new[old_bundle_uuid]
                        if new_bundle_uuid in created_uuids:  # Only add novel bundles
                            # Add prelude
                            if not skip_prelude:
                                for item2 in prelude_items:
                                    # Create a copy of the item on the destination worksheet
                                    item2 = item2.copy()
                                    item2['worksheet'] = JsonApiRelationship(
                                        'worksheets', worksheet_uuid
                                    )
                                    client.create(
                                        'worksheet-items',
                                        data=item2,
                                        params={'uuid': worksheet_uuid},
                                    )

                            # Add the bundle item
                            client.create(
                                'worksheet-items',
                                data={
                                    'type': worksheet_util.TYPE_BUNDLE,
                                    'worksheet': JsonApiRelationship('worksheets', worksheet_uuid),
                                    'bundle': JsonApiRelationship('bundles', new_bundle_uuid),
                                },
                                params={'uuid': worksheet_uuid},
                            )
                            new_bundle_uuids_added.add(new_bundle_uuid)

                if (item['type'] == worksheet_util.TYPE_MARKUP and item['value'] != '') or item[
                    'type'
                ] == worksheet_util.TYPE_DIRECTIVE:
                    prelude_items.append(item)  # Include in prelude
                else:
                    prelude_items = []  # Reset

        # Add the bundles that haven't been added yet
        for info, new_info in plan:
            new_bundle_uuid = new_info['uuid']
            if new_bundle_uuid not in new_bundle_uuids_added:
                print('adding: ' + new_bundle_uuid)
                client.create(
                    'worksheet-items',
                    data={
                        'type': worksheet_util.TYPE_BUNDLE,
                        'worksheet': JsonApiRelationship('worksheets', worksheet_uuid),
                        'bundle': JsonApiRelationship('bundles', new_bundle_uuid),
                    },
                    params={'uuid': worksheet_uuid},
                )

    return plan


def check_bundle_not_frozen(bundle):
    if bundle.frozen:
        raise PermissionError(
            'Cannot mutate frozen bundle %s(%s).' % (bundle.uuid, bundle.metadata.to_dict()["name"])
        )


def check_bundle_freezable(bundle):
    if bundle.state not in State.FINAL_STATES:
        raise PermissionError(
            'Cannot freeze bundle %s(%s), bundle is not in a final state.'
            % (bundle.uuid, bundle.metadata.to_dict()["name"])
        )


def get_bundle_state_details(bundle):
    """
    This helper returns information about the given bundle's status based on
    the bundle's current `state` and `run_status`.

    If the bundle is currently running, its `run_status` will be returned.
    Otherwise, a description of the `state` is returned.

    See bundle_state.py for details on the State class.
    See Bundle-Lifecycle.md for public bundle state documentation.
    """
    metadata = bundle.get('metadata', {})
    run_status = metadata.get('run_status')
    type = bundle.get('bundle_type')
    state = bundle.get('state')
    state_details_by_type = {
        'dataset': {  # uploaded
            'created': 'Bundle has been created but its contents have not been uploaded yet.',
            'uploading': 'Bundle contents are being uploaded.',
            'ready': 'Bundle has finished uploading successfully, and is ready to be used for further runs.',
            'failed': 'Bundle uploading failed.',
        },
        'make': {
            'created': 'Bundle has been created but its contents have not yet been populated.',
            'making': 'Bundle contents are being populated by copying its dependencies.',
            'ready': 'Bundle contents have been successfully populated and is ready for further runs.',
            'failed': 'Populating bundle contents failed.',
        },
        'run': {
            'created': 'Bundle has been created but its contents have not been populated yet.',
            'staged': 'Bundle’s dependencies are all ready. Waiting for the bundle to be assigned to a worker to be run.',
            'starting': 'Bundle has been assigned to a worker. Waiting for worker to start the bundle.',
            'finalizing': 'Bundle command has finished executing, cleaning up on the worker.',
            'ready': 'Bundle command has finished executing successfully, and results have been uploaded to the server.',
            'failed': 'Bundle has failed.',
            'killed': 'Bundle was killed by the user. Bundle contents populated based on when the bundle was killed.',
            'worker_offline': 'The worker where the bundle is running on is offline, and the worker might or might not come back online.',
        },
    }

    # We can remove the defensive checks below once program bundles are converted to dataset bundles.
    # Related Issue: https://github.com/codalab/codalab-worksheets/issues/4235
    state_details = state_details_by_type.get(type, {}).get(state, '')

    if state == 'preparing' or state == 'running':
        return run_status
    return state_details
