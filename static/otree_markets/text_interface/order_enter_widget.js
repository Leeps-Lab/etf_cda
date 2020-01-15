import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';

class OrderEnterWidget extends PolymerElement {

    static get properties() {
        return {
        };
    }

    static get template() {
        return html`
            <style>
            </style>

            <div id="container">
                <label for="price_input">Price</label>
                <input id="price_input" type="number" min="0">
                <button type="button" on-click="_enter_order" value="bid">Enter Bid</button>
                <button type="button" on-click="_enter_order" value="ask">Enter Ask</button>
            </div>
        `;
    }

    _enter_order(event) {
        const price = parseInt(this.$.price_input.value);
        const is_bid = (event.target.value == "bid");
        const order = {
            price: price,
            is_bid: is_bid,
        }
        this.dispatchEvent(new CustomEvent('order-entered', {detail: order}));
    }

}

window.customElements.define('order-enter-widget', OrderEnterWidget);
