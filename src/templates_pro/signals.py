"""Invalidate cached blocks/constants whenever they change."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import SiteConstant, TemplateBlock
from .services import bump_version


@receiver([post_save, post_delete], sender=TemplateBlock)
def _blocks_changed(**kwargs):
    bump_version("blocks")


@receiver([post_save, post_delete], sender=SiteConstant)
def _constants_changed(**kwargs):
    bump_version("constants")
