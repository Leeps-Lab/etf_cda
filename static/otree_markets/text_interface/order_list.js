import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
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
                #container div {
                    border: 1px solid black;
                    text-align: center;
                    margin: 3px;
                }
            </style>

            <div id="container">
                <template is="dom-repeat" items="{{orders}}">
                    <div>$[[item.price]]</div>
                </template>
            </div>
        `;
    }

}

window.customElements.define('order-list', OrderList);
