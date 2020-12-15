import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';

import '/static/otree-redwood/src/otree-constants/otree-constants.js';

/*
    this component is a message box which displays either info messages or error messages.
    call either the `info` or `error` method with a message to add a message to the list.
    the box always stays scrolled to the bottom unless the player has scrolled the message box up at all
*/

export class EventLog extends PolymerElement {

    static get properties() {
        return {
            // if set, the max number of entries shown will be limited to this number
            maxEntries: Number,
            _entries: {
                type: Array,
                value: function() {
                    return [];
                },
            },
            // true if the player is scrolled to the bottom of the log
            _scrolled_to_bottom: {
                type: Boolean,
                value: true,
            }
        };
    }

    static get template() {
        return html`
            <style>
                #container {
                    width: 100%;
                    height: 100%;
                    padding: 10px;
                    overflow-y: scroll;
                    box-sizing: border-box;
                }
                #container div {
                    font-family: monospace;
                }
                .error {
                    color: red;
                }
                .warn {
                    color: darkorange;
                }
            </style>

            <otree-constants
                id="constants"
            ></otree-constants>

            <div id="container" on-scroll="_container_scroll">
                <template is="dom-repeat" items="{{_entries}}">
                    <div>
                        <span class$="[[item.type]]">[[item.text]]</span>
                    </div>
                </template>
            </div>
        `;
    }

    ready() {
        super.ready();

        const round_number = this.$.constants.roundNumber;
        // check if log contents are stored in session storage
        const prev_data = JSON.parse(sessionStorage.getItem('event-log-data'));
        if (prev_data !== null && prev_data.round_number == round_number) {
            this.set('_entries', prev_data.entries);
        }
        // write log contents into session storage on page unload
        window.addEventListener('unload', () => {
            const new_data = JSON.stringify({
                entries: this.get('_entries'),
                round_number: round_number,
            });
            console.log(new_data);
            sessionStorage.setItem('event-log-data', new_data);
        });

        setTimeout(() => {
            const container = this.$.container;
            container.scrollTop = container.scrollHeight- container.clientHeight;
        })
    }

    add(text, type) {
        this.push('_entries', {
            type: type,
            text: text,
        });
        
        if (this.maxEntries && this._entries.length > this.maxEntries) {
            this.shift('_entries');
        }

        if (this._scrolled_to_bottom) {
            // have to wait because we need to calculate scrollTop after the new entry is added
            setTimeout(() => {
                const container = this.$.container;
                container.scrollTop = container.scrollHeight- container.clientHeight;
            });
        }
    }

    error(text) {
        this.add(text, 'error');
    }

    info(text) {
        this.add(text, 'info');
    }

    warn(text) {
        this.add(text, 'warn');
    }

    _container_scroll(event) {
        const container = event.target;
        this._scrolled_to_bottom = (container.scrollHeight - container.clientHeight <= container.scrollTop + 1);
    }

}

window.customElements.define('event-log', EventLog);
