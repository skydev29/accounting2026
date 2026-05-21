/** @odoo-module */

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.MoyasarModal = publicWidget.Widget.extend({
    selector: '.moyasar-modal',
    events: {
        'click .close-moyasar-form': '_onCloseMoyasarForm',
    },
    _onCloseMoyasarForm() {
        $('#wrapwrap').css('z-index', 1051);
        window.location.reload();
    },
});

publicWidget.registry.MoyasarFormRender = publicWidget.Widget.extend({
    selector: '#o_payment_methods',
    start() {
        return this._super(...arguments);
    },
});

export const moyasarModal = publicWidget.registry.MoyasarModal;
export const moyasarFormRender = publicWidget.registry.MoyasarFormRender;
