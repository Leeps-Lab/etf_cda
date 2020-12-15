import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';

/*
    this component represents a list of trades which have occured in this market.
    it expects `trades` to be a sorted list of objects representing trades
*/

export class TradeList extends PolymerElement {

    static get properties() {
        return {
            trades: Array,
            assetName: String,
            displayFormat: {
                type: Object,
                value: function() {
                    return (making_order, taking_order) => `${making_order.traded_volume} @ $${making_order.price}`;
                },
            },
        };
    }

    static get template() {
        return html`
            <style>
                #container {
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

            <div id="container">
                <template is="dom-repeat" items="{{trades}}" as="trade" filter="{{_getAssetFilterFunc(assetName)}}">
                    <template is="dom-repeat" items="{{trade.making_orders}}" as="making_order">
                        <div>
                            <span>[[displayFormat(making_order, trade.taking_order)]]</span>
                        </div>
                    </template>
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
