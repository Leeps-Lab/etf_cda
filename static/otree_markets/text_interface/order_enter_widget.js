import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';

class OrderEnterWidget extends PolymerElement {

    static get properties() {
        return {
            cash: Number,
            assets: Object,
        };
    }

    static get template() {
        return html`
            <style>
                #container {
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }
                #container > div {
                    margin: 5px;
                    padding: 5px;
                    border: 1px solid black;
                }
                #container h4 {
                    margin: 0.2em;
                }
                #order-input {
                    text-align: center;
                }
                #allocation > div:first-child {
                    text-align: center;
                }
            </style>

            <div id="container">
                <div id="allocation">
                    <div>
                        <h4>Your Allocation</h4>
                    </div>
                    <div>Cash: $[[cash]]</div>
                    <div>Assets: [[assets.A]]</div>
                </div>
                <div id="order-input">
                    <h4>Submit an Order</h4>
                    <label for="price_input">Price</label>
                    <input id="price_input" type="number" min="0">
                    <label for="volume_input">Volume</label>
                    <input id="volume_input" type="number" min="1">
                    <div>
                        <button type="button" on-click="_enter_order" value="bid">Enter Bid</button>
                        <button type="button" on-click="_enter_order" value="ask">Enter Ask</button>
                    </div>
                </div>
            </div>
        `;
    }

    _enter_order(event) {
        const price = parseInt(this.$.price_input.value);
        const volume = parseInt(this.$.volume_input.value);
        const is_bid = (event.target.value == "bid");
        const order = {
            price: price,
            volume: volume,
            is_bid: is_bid,
            asset_name: 'A',
        }
        this.dispatchEvent(new CustomEvent('order-entered', {detail: order}));
    }

}

window.customElements.define('order-enter-widget', OrderEnterWidget);
