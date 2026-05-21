/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * DeprecLinesToggler — OWL field widget for account.asset.depreciation.line
 *
 * Shows a coloured circle button on each depreciation board line.
 * When clicked (and the line is not yet posted), calls create_move on the
 * server, then refreshes the parent record.
 *
 *  Grey   = not linked to any journal entry  → clickable → creates entry
 *  Orange = entry exists but not yet posted  → disabled
 *  Green  = entry posted                     → disabled
 */
export class DeprecLinesToggler extends Component {
    static template = "bi_account_asset.DeprecLinesToggler";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
    }

    get isPosted() {
        return this.props.record.data.move_posted_check;
    }

    get hasMove() {
        return this.props.record.data.move_check;
    }

    get isDisabled() {
        return this.isPosted || this.hasMove;
    }

    get title() {
        if (this.isPosted) {
            return "Posted";
        }
        if (this.hasMove) {
            return "Accounting entries waiting for manual verification";
        }
        return "Click to create depreciation entry";
    }

    async onClick(ev) {
        ev.stopPropagation();
        if (this.isDisabled) {
            return;
        }
        await this.orm.call(
            "account.asset.depreciation.line",
            "create_move",
            [[this.props.record.resId]]
        );
        await this.props.record.model.load({ resId: this.props.record.resId });
    }
}

registry.category("fields").add("deprec_lines_toggler", {
    component: DeprecLinesToggler,
    supportedTypes: ["boolean"],
});
