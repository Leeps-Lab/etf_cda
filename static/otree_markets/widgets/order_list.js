import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';

/*
    this component represents a list of orders in the market. it expects
    `orders` to be an appropriately sorted list of order objects.
    additionally, it adds a red X to this player's orders and emits an 'order-canceled' event
    when the X is clicked
*/

class OrderList extends PolymerElement {

    static get properties() {
        return {
            orders: Array,
            assetName: String,
        };
    }

    static get template() {
        return html`
            <style>
                #container {
                    border: 1px solid black;
                    width: 100%;
                    height: 100%;
                    overflow-y: auto;
                    box-sizing: border-box;
                }
                #container > div {
                    position: relative;
                    border: 1px solid black;
                    text-align: center;
                    margin: 3px;
                }
                .my-order {
                    background-color: lightgreen;
                }
                .cancel-button {
                    position: absolute;
                    color: red;
                    line-height: 0.85;
                    height: 100%;
                    right: 10px;
                    font-size: 150%;
                    cursor: pointer;
                    user-select: none;
                }
                .other-order .cancel-button {
                    display: none;
                }
            </style>

            <otree-constants
                id="constants"
            ></otree-constants>

            <div id="container">
                <template is="dom-repeat" items="{{orders}}" filter="{{_getAssetFilterFunc(assetName)}}">
                    <div class$="[[_getOrderClass(item)]]">
                        <span>[[item.volume]]</span><span>@</span><span>$[[item.price]]</span>
                        <span class="cancel-button" on-click="_cancelOrder">&#9746;</span>
                    </div>
                </template>
            </div>
        `;
    }

    _getAssetFilterFunc(assetName) {
        if(!assetName) {
            return null;
        }
        return function(order) {
            return order.asset_name == assetName;
        }
    }

    _getOrderClass(order) {
        if (order.pcode == this.$.constants.participantCode)
            return 'my-order';
        else
            return 'other-order';
    }

    _cancelOrder(event) {
        const order = event.model.item;
        this.dispatchEvent(new CustomEvent('order-canceled', {detail: order, bubbles: true, composed: true}));
    }

}

window.customElements.define('order-list', OrderList);
