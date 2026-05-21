# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountBudgetPost(models.Model):
    _name = "account.budget.post"
    _order = "name"
    _description = "Budgetary Position"

    name = fields.Char('Name', required=True)
    account_ids = fields.Many2many(
        'account.account', 'account_budget_rel', 'budget_id', 'account_id',
        string='Accounts',
    )
    crossovered_budget_line = fields.One2many(
        'crossovered.budget.lines', 'general_budget_id', 'Budget Lines',
    )
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env.company,
    )

    def _check_account_ids(self, vals):
        # Raise an error to prevent account.budget.post from having no account_ids.
        # This check is done because required=True doesn't work on Many2many fields.
        if 'account_ids' in vals:
            account_ids = self.new(vals).account_ids
        else:
            account_ids = self.account_ids
        if not account_ids:
            raise ValidationError(_('The budget must have at least one account.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_account_ids(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._check_account_ids(vals)
        return super().write(vals)


class CrossoveredBudget(models.Model):
    _name = "crossovered.budget"
    _description = "Budget"
    _inherit = ['mail.thread']

    name = fields.Char('Budget Name', required=True)
    creating_user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user,
    )
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done'),
    ], string='Status', default='draft', index=True, required=True,
        readonly=True, copy=False, tracking=True)
    crossovered_budget_line = fields.One2many(
        'crossovered.budget.lines', 'crossovered_budget_id', 'Budget Lines', copy=True,
    )
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env.company,
    )
    pertial = fields.Boolean(string='Allow Partial')
    project_id = fields.Many2one('project.project', string='Project')
    analytic_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',
        related='project_id.account_id',
    )

    @api.onchange('date_to', 'date_from')
    def _onchange_date(self):
        if self.date_to and self.date_from and self.date_from > self.date_to:
            raise UserError(_("Please select a proper date."))

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partial = self.env['ir.config_parameter'].sudo().get_param(
            'bi_account_budget.partial_budget_approve', False
        )
        res['pertial'] = partial not in (False, 'False', '0', '')
        return res

    def action_budget_confirm(self):
        self.write({'state': 'confirm'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_validate(self):
        self.write({'state': 'validate'})

    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    def action_budget_done(self):
        self.write({'state': 'done'})


class CrossoveredBudgetLines(models.Model):
    _name = "crossovered.budget.lines"
    _description = "Budget Line"
    _rec_name = 'crossovered_budget_id'

    crossovered_budget_id = fields.Many2one(
        'crossovered.budget', 'Budget', ondelete='cascade', index=True, required=True,
    )
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    general_budget_id = fields.Many2one('account.budget.post', 'Budgetary Position', required=True)
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    paid_date = fields.Date('Paid Date')
    planned_amount = fields.Float('Planned Amount', required=True, digits=0)
    practical_amount = fields.Float(
        compute='_compute_practical_amount', string='Practical Amount', digits=0,
    )
    theoritical_amount = fields.Float(
        compute='_compute_theoritical_amount', string='Theoretical Amount', digits=0,
    )
    percentage = fields.Float(compute='_compute_percentage', string='Achievement')
    company_id = fields.Many2one(
        related='crossovered_budget_id.company_id', comodel_name='res.company',
        string='Company', store=True, readonly=True,
    )
    pertial_id = fields.Boolean(related='crossovered_budget_id.pertial')
    pertial_amount = fields.Float(string='Partial Amount')

    @api.onchange('date_to', 'date_from')
    def _onchange_date(self):
        if self.date_to and self.date_from and self.date_from > self.date_to:
            raise UserError(_("Please select a proper date."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.crossovered_budget_id and rec.crossovered_budget_id.analytic_id:
                rec.analytic_account_id = rec.crossovered_budget_id.analytic_id
        return records

    def _compute_practical_amount(self):
        for line in self:
            result = 0.0
            acc_ids = line.general_budget_id.account_ids.ids
            date_to = self.env.context.get('wizard_date_to') or line.date_to
            date_from = self.env.context.get('wizard_date_from') or line.date_from
            if not acc_ids or not date_from or not date_to:
                line.practical_amount = 0.0
                continue
            if line.analytic_account_id.id:
                self.env.cr.execute("""
                    SELECT SUM(amount)
                    FROM account_analytic_line
                    WHERE account_id = %s
                        AND date BETWEEN %s AND %s
                        AND general_account_id = ANY(%s)
                """, (line.analytic_account_id.id, date_from, date_to, acc_ids))
                result = self.env.cr.fetchone()[0] or 0.0
            else:
                self.env.cr.execute("""
                    SELECT SUM(credit) - SUM(debit)
                    FROM account_move_line
                    WHERE account_id = ANY(%s)
                        AND date BETWEEN %s AND %s
                """, (acc_ids, date_from, date_to))
                result = self.env.cr.fetchone()[0] or 0.0
            line.practical_amount = result

    def _compute_theoritical_amount(self):
        today = fields.Date.today()
        for line in self:
            theo_amt = 0.0

            if self.env.context.get('wizard_date_from') and self.env.context.get('wizard_date_to'):
                ctx_from = fields.Date.to_date(self.env.context['wizard_date_from'])
                ctx_to = fields.Date.to_date(self.env.context['wizard_date_to'])

                date_from = line.date_from if ctx_from < line.date_from else ctx_from
                if ctx_from > line.date_to:
                    date_from = False

                date_to = line.date_to if ctx_to > line.date_to else ctx_to
                if ctx_to < line.date_from:
                    date_to = False

                if date_from and date_to:
                    line_timedelta = line.date_to - line.date_from
                    elapsed_timedelta = date_to - date_from
                    if elapsed_timedelta.days > 0 and line_timedelta.days > 0:
                        base = line.pertial_amount if line.pertial_amount > 0 else line.planned_amount
                        theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * base
            else:
                if line.paid_date:
                    if line.date_to > line.paid_date:
                        theo_amt = line.pertial_amount if line.pertial_amount > 0 else line.planned_amount
                    else:
                        theo_amt = 0.0
                else:
                    if not line.date_from or not line.date_to:
                        theo_amt = 0.0
                    else:
                        line_timedelta = line.date_to - line.date_from
                        elapsed_timedelta = today - line.date_from

                        if elapsed_timedelta.days < 0:
                            theo_amt = 0.0
                        elif line_timedelta.days > 0 and today < line.date_to:
                            base = line.pertial_amount if line.pertial_amount > 0 else line.planned_amount
                            theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * base
                        else:
                            theo_amt = line.pertial_amount if line.pertial_amount > 0 else line.planned_amount

            line.theoritical_amount = theo_amt

    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.0:
                line.percentage = (line.practical_amount or 0.0) / line.theoritical_amount * 100
            else:
                line.percentage = 0.0
