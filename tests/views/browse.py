# -*- coding: utf-8 -*-
#
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from pytest_pootle.utils import as_dir, url_name


@pytest.mark.django_db
@pytest.mark.parametrize('url', [
    '/projects/',
    '/projects/project0/',
    '/language0/',
    '/language0/project0/',
    '/language0/project0/store0.po',
    '/language0/project0/subdir0/',
    '/language0/project0/subdir0/store4.po',
])
def test_browse(client, request_users, test_name, flush_redis,
                snapshot_stack, url):
    """Tests correctness of the browsing view context."""
    user = request_users['user']

    with snapshot_stack.push([
        as_dir(test_name), as_dir(user.username), url_name(url)
    ]):
        if not user.is_anonymous():
            client.login(username=user.username, password=user.password)
        response = client.get(url)
        assert response.status_code == 200

        with snapshot_stack.push('context') as snapshot:
            snapshot.assert_matches(response.context)
