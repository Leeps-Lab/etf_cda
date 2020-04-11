import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '../widgets/order_list.js';
import '../widgets/trade_list.js';

/*
    this component is the main entry point for the text interface frontend. it maintains the market state in
    the `bids`, `asks` and `trades` array properties and coordinates communication with the backend
*/

class AssetCell extends PolymerElement {

    static get properties() {
        return {
            assetName: String,
            bids: Array,
            asks: Array,
            trades: Array,
        };
    }

    static get template() {
        return html`
            <style>
                * {
                    box-sizing: border-box;
                }
                .main-container {
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                }
                h3, h5 {
                    margin: 0;
                    text-align: center;
                }

                .list {
                    flex: 1;
                    display: flex;
                    padding: 0 2px 0 2px;
                }
                .list > div {
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                    flex: 1;
                    margin: 0 2px 0 2px;
                }
                .list > div > :last-child {
                    flex: 1;
                }

                .buttons > div {
                    display: flex;
                    align-items: center;
                    width: 33%;
                    height: 100%;
                    padding: 5px;
                }
                .buttons > div:first-child {
                    float: left;
                }
                .buttons > div:last-child {
                    float: right;
                }
                .buttons input {
                    flex: 1;
                    min-width: 40px;
                }
                .buttons > div > * {
                    margin: 5px;
                }
            </style>

            <div class="main-container">
                <h3>Asset [[assetName]]</h3>
                <div class="list">
                    <div>
                        <h5>Bids</h5>
                        <order-list
                            asset-name="[[assetName]]"
                            orders="[[bids]]"
                        ></order-list>
                    </div>
                    <div>
                        <h5>Trades</h5>
                        <trade-list
                            asset-name="[[assetName]]"
                            trades="[[trades]]"
                        ></trade-list>
                    </div>
                    <div>
                        <h5>Asks</h5>
                        <order-list
                            asset-name="[[assetName]]"
                            orders="[[asks]]"
                        ></order-list>
                    </div>
                </div>
                <div class="buttons">
                    <div>
                        <label for="bid_price">Price</label>
                        <input id="bid_price" type="number" min="0">
                        <button type="button" on-click="_enter_order" value="bid">Buy</button>
                    </div>
                    <div>
                        <label for="ask_price">Price</label>
                        <input id="ask_price" type="number" min="0">
                        <button type="button" on-click="_enter_order" value="ask">Sell</button>
                    </div>
                </div>
            </div>
        `;
    }

    _enter_order(event) {
        const is_bid = (event.target.value == 'bid');
        const price = parseInt(this.$[is_bid ? 'bid_price' : 'ask_price'].value);
        const order = {
            price: price,
            // unit volume
            volume: 1,
            is_bid: is_bid,
            asset_name: this.assetName,
        }
        this.dispatchEvent(new CustomEvent('order-entered', {detail: order}));
    }

}

window.customElements.define('asset-cell', AssetCell);
