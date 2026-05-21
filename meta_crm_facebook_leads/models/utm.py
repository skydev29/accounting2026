import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class UtmMedium(models.Model):
    _inherit = 'utm.medium'

    facebook_ad_id = fields.Char()

    _facebook_ad_unique = models.Constraint(
        'unique(facebook_ad_id)',
        'This Facebook Ad already exists!'
    )


class UtmAdset(models.Model):
    _name = 'utm.adset'
    _description = 'UTM Adset'

    name = fields.Char()
    facebook_adset_id = fields.Char()

    _facebook_adset_unique = models.Constraint(
        'unique(facebook_adset_id)',
        'This Facebook AdSet already exists!'
    )


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    facebook_campaign_id = fields.Char()

    _facebook_campaign_unique = models.Constraint(
        'unique(facebook_campaign_id)',
        'This Facebook Campaign already exists!'
    )
