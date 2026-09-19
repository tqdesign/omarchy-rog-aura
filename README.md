# Under glow

Colours and Aura effects for the lights under a ROG Strix laptop.

An [Omarchy](https://omarchy.org/) bar plugin that talks to
[asusctl](https://asus-linux.org/) / `asusd`. Built on a ROG Strix G18; it
should also work on other ROG machines that expose Aura over D-Bus.

## Install

```bash
omarchy plugin add https://github.com/tqdesign/omarchy-rog-aura.git --enable --yes
omarchy bar move tqdesign.rog-aura --section right
```

The chip is a colour circle on the **right** of the bar, next to Power.

From a local checkout:

```bash
omarchy plugin add /path/to/omarchy-rog-aura --enable --yes
omarchy bar move tqdesign.rog-aura --section right
```

Needs `asusctl` (already installed on Omarchy ROG machines).

Already installed? Pull the latest:

```bash
omarchy plugin update tqdesign.rog-aura --yes
omarchy restart shell
```

## What it does

- Live colour picker for the under-glow (lightbar). Palette, RGB sliders, or hex.
- Factory Aura effects (Static, Breathe, Cycle, Wave, Stars, Rain, Highlight,
  Laser, Ripple, Pulse, Comet, Flash). Speed and direction when the effect
  uses them.
- Animated modes are also driven on the **under glow**. The factory firmware
  often only animates the keyboard; the plugin paints the lightbar itself.
- Keyboard and under glow share colour and effect, and can be turned on or
  off independently.
- Closing the lid turns the lights off, including clamshell mode with an
  external monitor. Opening the lid restores the previous on/off state.

Cycle, Wave, and Rain do not take a picked colour, so those controls hide.

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
- **Effect** — every Aura mode `asusd` reports. Speed and direction appear
  when the effect uses them.

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
python3 aura.py apply '{"action":"effect","mode":"rainbow-wave","speed":"high","direction":"right"}'
python3 aura.py apply '{"action":"power","zone":"lightbar","awake":true,"boot":true}'
python3 aura.py apply '{"action":"brightness","value":"high"}'
python3 aura.py lid
```

## Tests

```bash
node Model.test.js
python3 aura_test.py
omarchy plugin validate .
```

## License

MIT. See [LICENSE](LICENSE).
