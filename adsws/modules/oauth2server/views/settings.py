# -*- coding: utf-8 -*-
#
# This file is part of ZENODO.
# Copyright (C) 2014 CERN.
#
# ZENODO is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ZENODO is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ZENODO. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.


"""
OAuth Server Settings Blueprint
"""

from __future__ import absolute_import
from functools import wraps

from flask import Blueprint, render_template, request, abort, redirect, \
    url_for, flash, session
from flask_login import login_required, current_user
from flask_menu import register_menu
from flask_breadcrumbs import register_breadcrumb
from flask import current_app

from adsws.core import db


from ..models import OAuthClient, OAuthToken
from ..forms import OAuthClientForm, OAuthTokenForm

blueprint = Blueprint(
    'oauth2server_settings',
    __name__,
    url_prefix="/account/settings/applications",
    static_folder="../static",
    template_folder="../templates",
)

#
# Decorator
#
def client_getter():
    """
    Decorator to retrieve Client object and check user permission
    """
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'client_id' not in kwargs:
                current_app.logger.error(
                    'Aborting with status code 500,'
                    ' client_id not found in args: {}'.format(kwargs))
                abort(500)

            client = OAuthClient.query.filter_by(
                client_id=kwargs.pop('client_id'),
                user_id=current_user.get_id(),
            ).first()

            if client is None:
                abort(404)

            return f(client, *args, **kwargs)
        return decorated
    return wrapper


def token_getter(is_personal=True, is_internal=False):
    """
    Decorator to retrieve Token object and check user permission
    """
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'token_id' not in kwargs:
                current_app.logger.error(
                    'Aborting with status code 500,'
                    ' token_id not found in args: {}'.format(kwargs))
                abort(500)

            token = OAuthToken.query.filter_by(
                id=kwargs.pop('token_id'),
                user_id=current_user.get_id(),
                is_personal=is_personal,
                is_internal=is_internal,
            ).first()

            if token is None:
                abort(404)

            return f(token, *args, **kwargs)
        return decorated
    return wrapper


#
# Views
#
@blueprint.route("/", methods=['GET', 'POST'])
@login_required
@register_menu(
    blueprint, 'settings.applications',
    'Applications',
    order=5,
    active_when=lambda: request.endpoint.startswith("oauth2server_settings.")
)
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.applications', 'Applications'
)
def index():
    clients = OAuthClient.query.filter_by(
        user_id=current_user.get_id(),
        is_internal=False,
    ).all()

    tokens = OAuthToken.query.options(db.joinedload('client')).filter(
        OAuthToken.user_id == current_user.get_id(),
        OAuthToken.is_personal == True,
        OAuthToken.is_internal == False,
        OAuthClient.is_internal == True,
    ).all()

    authorized_apps = OAuthToken.query.options(db.joinedload('client')).filter(
        OAuthToken.user_id == current_user.get_id(),
        OAuthToken.is_personal == False,
        OAuthToken.is_internal == False,
        OAuthClient.is_internal == False,
    ).all()

    return render_template(
        "oauth2server/settings/index.html",
        clients=clients,
        tokens=tokens,
        authorized_apps=authorized_apps,
    )


@blueprint.route("/clients/new/", methods=['GET', 'POST'])
@login_required
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.applications.client_new', 'New'
)
def client_new():
    form = OAuthClientForm(request.form)

    if form.validate_on_submit():
        c = OAuthClient(user_id=current_user.get_id())
        c.gen_salt()
        form.populate_obj(c)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for(".client_view", client_id=c.client_id))

    return render_template(
        "oauth2server/settings/client_new.html",
        form=form,
    )


@blueprint.route("/clients/<string:client_id>/", methods=['GET', 'POST'])
@login_required
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.applications.client_edit', 'Edit'
)
@client_getter()
def client_view(client):
    if request.method == "POST" and 'delete' in request.form:
        db.session.delete(client)
        db.session.commit()
        return redirect(url_for('.index'))

    form = OAuthClientForm(request.form, client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()

    return render_template(
        "oauth2server/settings/client_view.html",
        client=client,
        form=form,
    )


@blueprint.route("/clients/<string:client_id>/reset/", methods=['POST'])
@login_required
@client_getter()
def client_reset(client):
    if request.form.get('reset') == 'yes':
        client.reset_client_secret()
        db.session.commit()
    return redirect(url_for('.client_view', client_id=client.client_id))


#
# Token views
#
@blueprint.route("/tokens/new/", methods=['GET', 'POST'])
@login_required
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.applications.token_new', 'New'
)
def token_new():
    form = OAuthTokenForm(request.form)

    if form.validate_on_submit():
        t = OAuthToken.create_personal(
            form.data['name'], current_user.get_id(), scopes = ['api:search','ads:default'],
        )
        flash('Please copy the personal access token now. You won\'t see it'
              ' again!', category='info')
        session['show_personal_access_token'] = True
        return redirect(url_for(".token_view", token_id=t.id))

    return render_template(
        "oauth2server/settings/token_new.html",
        form=form,
    )


@blueprint.route("/tokens/<string:token_id>/", methods=['GET', 'POST'])
@login_required
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.applications.token_edit', 'Edit'
)
@token_getter()
def token_view(token):
    if request.method == "POST" and 'delete' in request.form:
        db.session.delete(token)
        db.session.commit()
        return redirect(url_for('.index'))

    show_token = session.pop('show_personal_access_token', False)

    form = OAuthTokenForm(request.form, token.client)
    if form.validate_on_submit():
        form.populate_obj(token.client)
        db.session.commit()

    return render_template(
        "oauth2server/settings/token_view.html",
        token=token,
        form=form,
        show_token=show_token,
    )


@blueprint.route("/tokens/<string:token_id>/revoke/", methods=['GET', ])
@login_required
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.applications.token_new', 'New'
)
@token_getter(is_personal=False, is_internal=False)
def token_revoke(token):
    db.session.delete(token)
    db.session.commit()
    return redirect(url_for('.index'))
