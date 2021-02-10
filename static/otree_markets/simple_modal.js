import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';

/*
    this component implements a simple modal that gives the user the choice to accept or decline something.
    to use: set the modal_text and on_close_callback properties then call the show method.
    on_close_callback will be called when the user selects one of the options. a boolean 'accepted' is passed
    to this function which reflects whether the user clicked accept or decline.
*/

export class SimpleModal extends PolymerElement {

    static get properties() {
        return {
            orders: Array,
            modal_text: String,
            on_close_callback: Object,
            buttons: {
                type: Array,
                value: () => ['Decline', 'Accept']
            }
        };
    }

    static get template() {
        return html`
            <style>
                :host {
                    display: none;
                    transition: opacity 0.1s linear;
                    opacity: 0;
                    position: absolute;
                    max-width: 40vw;
                    left: 50%;
                    top: 30%;
                    transform: translate(-50%, -50%);
                    z-index: 1;
                }
                #container {
                    display: flex;
                    flex-direction: column;
                    background-color: #dae0e5;
                    border: 1px solid black;
                    box-shadow: 5px 5px #a5a9ad91;
                }
                #container > div {
                    text-align: center;
                    margin: 10px;
                }
                #container > div:first-child {
                    flex: 1 1 auto;
                    padding: 10px;
                }
            </style>

            <div id="container">
                <div>[[modal_text]]</div>
                <div>
                    <template is="dom-repeat" items="{{buttons}}">
                        <button type="button" value="{{ index }}" on-click="_button_click">{{ item }}</button>
                    </template>
                </div>
            </div>
        `;
    }

    // called from outside the component, displays the modal
    show() {
        this.style.display = 'initial';
        // need to wait to set opacity,
        // changing display and opacity in same tick prevents transition from showing
        setTimeout(() => {
            this.style.opacity = 1;
        });
    }

    _button_click(event) {
        this.style.opacity = 0;
        // set display to none when opacity transition has finished
        this.addEventListener('transitionend', () => {
            this.style.display = 'none';
        }, {once: true});

        const button_index = parseInt(event.target.value);
        this.on_close_callback(button_index);
    }

}

window.customElements.define('simple-modal', SimpleModal);
