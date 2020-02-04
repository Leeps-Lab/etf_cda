import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';

class OrderList extends PolymerElement {

    static get properties() {
        return {
            orders: Array,
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
                }
                .other-order .cancel-button {
                    display: none;
                }
            </style>

            <otree-constants
                id="constants"
            ></otree-constants>

            <div id="container">
                <template is="dom-repeat" items="{{orders}}">
                    <div class$="[[_getOrderClass(item)]]">
                        <span>$[[item.price]]</span>
                        <span class="cancel-button" on-click="_cancelOrder">&#9746;</span>
                    </div>
                </template>
            </div>
        `;
    }

    _getOrderClass(order) {
        if (order.pcode == this.$.constants.participantCode) {
            return 'my-order';
        }
        else {
            return 'other-order';
        }
    }

    _cancelOrder(event) {
        const order = event.model.item;
        this.dispatchEvent(new CustomEvent('order-canceled', {detail: order}));
    }

}

window.customElements.define('order-list', OrderList);
