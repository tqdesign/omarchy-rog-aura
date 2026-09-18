# Under glow

Colours and Aura effects for the lights under a ROG Strix laptop.

An [Omarchy](https://omarchy.org/) bar plugin that talks to
[asusctl](https://asus-linux.org/) / `asusd`. Built on a ROG Strix G18; it
should also work on other ROG machines that expose Aura over D-Bus.

On this hardware the **under glow** (lightbar) and **keyboard** share one
colour and effect. Each zone can still be turned on or off on its own.
Closing the lid turns the lights off (including clamshell mode with an
external monitor) and restores them when you open it.

## Install

```bash
omarchy plugin add https://github.com/tqdesign/omarchy-rog-aura.git --enable --yes
omarchy bar move tqdesign.rog-aura --section right
```

From a local checkout:

```bash
omarchy plugin add /path/to/omarchy-rog-aura --enable --yes
omarchy bar move tqdesign.rog-aura --section right
```

Needs `asusctl` (already installed on Omarchy ROG machines).

## Bar

The chip is a live swatch of the current colour.

| Click | Action |
| --- | --- |
| Left | Open the panel |
| Right | Toggle the under glow (lightbar) |
| Middle | Next effect |
| Scroll | Cycle brightness |

## Panel

- **Zones** — independently turn the under glow and keyboard on or off
- **Stay on while sleeping** — keep the lightbar lit through suspend. Closing
  the lid always turns the lights off.
- **Brightness** — Off / Low / Med / High
- **Colour** — palette, RGB sliders, and a hex field. The lights follow as
  you pick. A second colour appears for Breathe and Stars.
- **Effect** — every Aura mode `asusd` reports (Static, Breathe, Cycle, Wave,
  Stars, Rain, Highlight, Laser, Ripple, Pulse, Comet, Flash). Speed and
  direction appear when the effect uses them.

Cycle, Wave, and Rain do not take a colour, so those controls hide.

## Commands

```bash
omarchy-shell tqdesign.rog-aura status
omarchy-shell tqdesign.rog-aura toggle
omarchy-shell tqdesign.rog-aura setColour ff0066
omarchy-shell tqdesign.rog-aura nextMode
omarchy-shell tqdesign.rog-aura toggleLightbar
```

The helper the panel uses:

```bash
python3 aura.py status
python3 aura.py apply '{"action":"effect","mode":"static","colour":"ff0066"}'
python3 aura.py apply '{"action":"power","zone":"lightbar","awake":true,"boot":true}'
python3 aura.py apply '{"action":"brightness","value":"high"}'
```

## Tests

```bash
node Model.test.js
python3 aura_test.py
omarchy plugin validate .
```

## License

MIT. See [LICENSE](LICENSE).
