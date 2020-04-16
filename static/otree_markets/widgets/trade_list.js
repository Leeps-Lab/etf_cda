import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';

/*
    this component represents a list of trades which have occured in this market.
    it expects `trades` to be a sorted list of objects representing trades
*/

class TradeList extends PolymerElement {

    static get properties() {
        return {
            trades: Array,
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
                <template is="dom-repeat" items="{{trades}}" filter="{{_getAssetFilterFunc(assetName)}}">
                    <div><span>$</span>{{item.making_orders.0.price}}</div>
                </template>
            </div>
        `;
    }

    _getAssetFilterFunc(assetName) {
        if(!assetName) {
            return null;
        }
        return function(trade) {
            return trade.asset_name == assetName;
        }
    }


}

window.customElements.define('trade-list', TradeList);
