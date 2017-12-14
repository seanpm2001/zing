# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
# Copyright (C) Zing contributors.
#
# This file is a part of the Zing project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.aggregates import Max
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from pootle.core.markup import MarkupField, get_markup_filter_display_name
from pootle.core.mixins import DirtyFieldsMixin

from .managers import PageManager


class AbstractPage(DirtyFieldsMixin, models.Model):

    active = models.BooleanField(
        _('Active'),
        default=False,
        help_text=_('Whether this page is active or not.'),
    )
    virtual_path = models.CharField(
        _("Virtual Path"),
        max_length=100,
        default='',
        unique=True,
        help_text='/pages/',
    )
    # TODO: make title and body localizable fields
    title = models.CharField(_("Title"), max_length=100)
    body = MarkupField(
        # Translators: Content that will be used to display this static page
        _("Display Content"),
        blank=True,
        help_text=_('Allowed markup: %s', get_markup_filter_display_name()),
    )
    modified_on = models.DateTimeField(
        default=now,
        editable=False,
    )

    objects = PageManager()

    class Meta(object):
        abstract = True

    def __unicode__(self):
        return self.virtual_path

    def save(self, **kwargs):
        # Update the `modified_on` timestamp only when specific fields change.
        if self.has_changes():
            self.modified_on = now()

        super(AbstractPage, self).save(**kwargs)

    def get_absolute_url(self):
        return reverse('pootle-staticpages-display', args=[self.virtual_path])

    @staticmethod
    def max_pk():
        """Returns the sum of all the highest PKs for each submodel."""
        return reduce(
            lambda x, y: x + y,
            [int(p.objects.aggregate(Max('pk')).values()[0] or 0)
             for p in AbstractPage.__subclasses__()],
        )

    def clean(self):
        """Fail validation if:

        - Body is blank
        - Current virtual path exists in other page models
        """
        if not self.body:
            # Translators: 'content' refer to a form field.
            raise ValidationError(_('Content must be provided.'))

        pages = [p.objects.filter(Q(virtual_path=self.virtual_path),
                                  ~Q(pk=self.pk),).exists() for p in
                 AbstractPage.__subclasses__()]
        if True in pages:
            raise ValidationError(_(u'Virtual path already in use.'))

    def has_changes(self):
        dirty_fields = self.get_dirty_fields()
        return any(field in dirty_fields for field in ('title', 'body'))


class LegalPage(AbstractPage):

    display_name = _('Legal Page')

    def get_edit_url(self):
        return reverse('pootle-staticpages-edit', args=['legal', self.pk])


class StaticPage(AbstractPage):

    display_name = _('Regular Page')

    def get_edit_url(self):
        return reverse('pootle-staticpages-edit', args=['static', self.pk])


class Agreement(models.Model):
    """Tracks who agreed a specific legal document and when."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    document = models.ForeignKey(LegalPage)
    agreed_on = models.DateTimeField(
        default=now,
        editable=False,
    )

    class Meta(object):
        unique_together = ('user', 'document',)

    def __unicode__(self):
        return u'%s (%s@%s)' % (self.document, self.user, self.agreed_on)

    def save(self, **kwargs):
        # When updating always explicitly renew agreement date
        if self.pk:
            self.agreed_on = now()

        super(Agreement, self).save(**kwargs)
