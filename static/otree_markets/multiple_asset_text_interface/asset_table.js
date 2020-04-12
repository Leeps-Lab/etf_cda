import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';

class AssetTable extends PolymerElement {

    static get properties() {
        return {
            cash: Number,
            assets: Object,
            bids: Array,
            asks: Array,
        };
    }

    static get observers() {
        return [
            '_observeBids(bids.splices)',
            '_observeAsks(asks.splices)',
        ];
    }

    static get template() {
        return html`
            <style>
                * {
                    box-sizing: border-box;
                }
                .container {
                    border: 1px solid black;
                    height: 100%;
                    padding: 20px;
                }

                .table {
                    width: 20em;
                    text-align: center;
                    margin-bottom: 20px;
                }
                .table > div {
                    display: flex;
                }
                .table span {
                    flex: 1;
                }
                .table .header {
                    border-bottom: 1px solid black;
                    font-weight: bold;
                }
            </style>

            <otree-constants
                id="constants"
            ></otree-constants>

            <div class="container">
                <div class="table">
                    <div class="header">
                        <span>Asset</span>
                        <span>Held</span>
                        <span>Requested</span>
                        <span>Offered</span>
                    </div>
                    <template is="dom-repeat" items="{{asset_names}}">
                        <div>
                            <span>[[item]]</span>
                            <span>[[_getHeldAsset(item, assets.*)]]</span>
                            <span>[[_getRequestedAsset(item, requested_assets.*)]]</span>
                            <span>[[_getOfferedAsset(item, offered_assets.*)]]</span>
                        </div>
                    </template>
                </div>
                <div>
                    <span>Cash: </span>
                    <span>[[cash]]</span>
                </div>
            </div>
        `;
    }

    ready() {
        super.ready();
        this.pcode = this.$.constants.participantCode;
        this.asset_names = Object.keys(this.assets);

        const requested = Object.fromEntries(this.asset_names.map(e => [e, 0]));
        for (let order of this.get('bids')) {
            if (order.pcode == this.pcode) {
                requested[order.asset_name]++;
            }
        }
        this.set('requested_assets', requested);

        const offered = Object.fromEntries(this.asset_names.map(e => [e, 0]));
        for (let order of this.get('asks')) {
            if (order.pcode == this.pcode) {
                offered[order.asset_name]++;
            }
        }
        this.set('offered_assets', offered);
    }

    _observeBids(bid_changes) {
        if (!bid_changes) return;
        for (let splice of bid_changes.indexSplices) {
            for (let order of splice.removed) {
                if (order.pcode == this.pcode) {
                    this._updateSubproperty('requested_assets', order.asset_name, -1);
                }
            }
            for (let i = splice.index; i < splice.index + splice.addedCount; i++) {
                const order = splice.object[i];
                if (order.pcode == this.pcode) {
                    this._updateSubproperty('requested_assets', order.asset_name, 1);
                }
            }
        }
    }

    _observeAsks(ask_changes) {
        if (!ask_changes) return;
        for (let splice of ask_changes.indexSplices) {
            for (let order of splice.removed) {
                if (order.pcode == this.pcode) {
                    this._updateSubproperty('offered_assets', order.asset_name, -1);
                }
            }
            for (let i = splice.index; i < splice.index + splice.addedCount; i++) {
                const order = splice.object[i];
                if (order.pcode == this.pcode) {
                    this._updateSubproperty('offered_assets', order.asset_name, 1);
                }
            }
        }
    }

    _updateSubproperty(property, subproperty, amount) {
        const old = this.get([property, subproperty]);
        this.set([property, subproperty], old + amount);
    }

    _getHeldAsset(asset_name, assets) {
        return assets.base[asset_name];
    }

    _getRequestedAsset(asset_name, requested_assets) {
        const requested = requested_assets.base[asset_name];
        return requested > 0 ? '+' + requested : '-';
    }

    _getOfferedAsset(asset_name, offered_assets) {
        const offered = offered_assets.base[asset_name];
        return offered > 0 ? '-' + offered : '-';
    }
}

window.customElements.define('asset-table', AssetTable);
