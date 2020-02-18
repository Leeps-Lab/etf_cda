import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';

class TradeList extends PolymerElement {

    static get properties() {
        return {
            trades: Array,
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

            <otree-constants
                id="constants"
            ></otree-constants>

            <div id="container">
                <template is="dom-repeat" items="{{trades}}">
                    <div>$[[item.timestamp]]</div>
                </template>
            </div>
        `;
    }

}

window.customElements.define('trade-list', TradeList);
