# Profiles and integrations worth exploring

Checked against publisher documentation on September 24, 2026. These are optional third-party products, not bundled dependencies. Their code, paid profiles and artwork are not redistributed in this repository.

## Development and AI

| Product | Type | Why it is relevant |
|---|---|---|
| [Stream Deck Companion for VS Code](https://marketplace.visualstudio.com/items?itemName=boylett.stream-deck-for-vscode) | Editor extension plus companion Stream Deck plugin | Sends text to the active terminal, runs editor commands by ID and follows the active VS Code window. A stronger editor integration than guessing context from a window title. |
| [Claude Code Shortcut Profile](https://marketplace.elgato.com/product/claude-code-shortcut-profile-491e5986-d93d-4471-a1fe-1d80b406000e) | Ready-made profile by Adx.cool | A dedicated Claude Code layout with icons, listed for Windows and several key grids. Useful to compare session controls and organization. Its listing is not evidence that every shortcut works with your CLI version. |
| [Microsoft PowerToys Hotkeys](https://marketplace.elgato.com/product/microsoft-powertoys-hotkeys-9b8f6f62-0ce0-4dd2-ac5c-edec33bc72f2) | Ready-made profile | Useful inspiration for Windows utilities. Its listed devices are Stream Deck +, XL and + XL; it is not advertised as a direct MK.2 import. |

Our Git keys use the local `AIDevTerminal` integration in the active PowerShell prompt. They do not require these editor plugins. An editor extension's terminal action is different from launching a new command window.

## Windows, screens and media

| Product | What it adds |
|---|---|
| [Win Tools by BarRaider](https://marketplace.elgato.com/product/win-tools-c17abe0e-f565-4d86-a80a-73b1d31c0c7d) | Per-application audio, individual clipboard keys, latency checks, services and virtual desktops. See the [publisher's feature list](https://barraider.com/) and [MK.2 compatibility](https://docs.barraider.com/faqs/general/compatibility/). |
| [Window Mover by Elgato](https://www.elgato.com/ca/en/explorer/products/marketplace/window-mover-for-stream-deck-organize-your-apps-instantly/) | Positions and sizes the foreground window, a specific application or a titled window on selected monitors. Multi Actions can arrange several windows together. |
| [SuperMacro by BarRaider](https://marketplace.elgato.com/product/supermacro-62195fec-7bcb-403d-b650-c342e9dfec67) | Programmable keyboard and mouse sequences. Useful for repetitive UI tasks with known focus; it does not identify a Git repository or prove a shell is ready. [Publisher documentation](https://docs.barraider.com/faqs/general/compatibility/). |
| [Volume Controller by Elgato](https://marketplace.elgato.com/product/volume-controller-34d9aa59-a41a-4a4c-a853-202ca91409e1) | Audio controls with bundled profiles and French/English support. |
| [HWiNFO Stream Deck plugin](https://github.com/moeilijk/hwinfo-streamdeck) | Real hardware sensor readings on keys. Requires a running, configured HWiNFO installation; sensor values are not supplied by our static profile generator. |

For an office layout, [Work Neo Profile by Elgato](https://marketplace.elgato.com/product/work-neo-profile-cc05cf0c-4aef-476e-88ea-37631f0e6c37) is a useful reference, but its target device is Neo, so adapt its organization to a 15-key deck.

Start with the integrations that improve an actual daily action. Keep the PowerShell Git page, use dedicated plugins when live app state matters, and assign [automatic app-specific profiles](https://www.elgato.com/uk/en/explorer/products/stream-deck/how-to-be-more-productive-with-stream-deck/) when you want the deck to follow the app in focus. Check current device, version and licensing requirements on each publisher page before installing.
