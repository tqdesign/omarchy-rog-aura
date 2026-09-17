# Under glow

Colours and Aura effects for the lights under a ROG Strix laptop. Talks to
[asusctl](https://asus-linux.org/) / `asusd`, so it works on this G18 and on
other ROG machines that expose Aura over D-Bus.

## Install

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

- **Zones** — independently turn the under glow and keyboard on or off. Colour
  and effect are shared on this hardware.
- **Stay on while sleeping** — keep the lightbar lit through sleep.
- **Brightness** — Off / Low / Med / High
- **Effect** — every Aura mode `asusd` reports (Static, Breathe, Cycle, Wave,
  Stars, Rain, Highlight, Laser, Ripple, Pulse, Comet, Flash)
- **Colour** — palette, RGB sliders, and a hex field. A second colour appears
  for Breathe and Stars. Speed and direction appear when the effect uses them.

## Commands

```bash
omarchy-shell tqdesign.rog-aura status
omarchy-shell tqdesign.rog-aura toggle
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
