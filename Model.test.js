const assert = require("assert")
const Model = require("./Model.js")

const sample = Model.parseStatus(JSON.stringify({
  ok: true,
  available: true,
  path: "/xyz/ljones/aura/19b6_2_4",
  mode: "static",
  modeId: 0,
  supportedModes: ["static", "breathe", "pulse", "nope"],
  colour: "#26BBD9",
  colour2: "000",
  speed: "Med",
  direction: "Right",
  brightness: "med",
  brightnessId: 2,
  supportedBrightness: ["off", "low", "med", "high"],
  zones: [
    { id: 1, name: "keyboard", label: "Keyboard", boot: true, awake: true, sleep: true, shutdown: true },
    { id: 2, name: "lightbar", label: "Under glow", boot: true, awake: true, sleep: false, shutdown: false }
  ]
}))

assert.strictEqual(sample.available, true)
assert.strictEqual(sample.colour, "26bbd9")
assert.strictEqual(sample.colour2, "000000")
assert.strictEqual(sample.speed, "med")
assert.strictEqual(sample.direction, "right")
assert.deepStrictEqual(sample.supportedModes, ["static", "breathe", "pulse"])
assert.strictEqual(Model.isGlowing(sample), true)
assert.strictEqual(Model.heroTitle(sample), "Static")
assert.strictEqual(Model.heroDetail(sample), "Live")
assert.strictEqual(Model.primaryZone(sample).name, "lightbar")
assert.strictEqual(Model.nextMode(sample), "breathe")

const offBar = JSON.parse(JSON.stringify(sample))
offBar.zones[1].awake = false
assert.strictEqual(Model.isGlowing(offBar), false)
assert.strictEqual(Model.heroDetail(offBar), "Under glow is off")

assert.strictEqual(Model.normalizeHex("#F0A"), "ff00aa")
assert.strictEqual(Model.hexFromRgb(38, 187, 217), "26bbd9")
assert.deepStrictEqual(Model.rgbFromHex("26bbd9"), { r: 38, g: 187, b: 217 })
assert.strictEqual(Model.cssColor("26bbd9"), "#26bbd9")

const effect = Model.effectPayload(sample, { mode: "breathe", colour: "ff0000" })
assert.strictEqual(effect.action, "effect")
assert.strictEqual(effect.mode, "breathe")
assert.strictEqual(effect.colour, "ff0000")
assert.strictEqual(effect.colour2, "000000")
assert.strictEqual(effect.speed, "med")
assert.strictEqual(effect.path, "/xyz/ljones/aura/19b6_2_4")
assert.strictEqual(effect.live, false)
assert.strictEqual(Model.effectPayload(sample, { colour: "00ff00", live: true }).live, true)

const toggleOff = Model.toggleZonePayload(sample, "lightbar")
assert.strictEqual(toggleOff.action, "power")
assert.strictEqual(toggleOff.zone, "lightbar")
assert.strictEqual(toggleOff.awake, false)

const toggleOn = Model.toggleZonePayload(offBar, "lightbar")
assert.strictEqual(toggleOn.awake, true)
assert.strictEqual(toggleOn.boot, true)
assert.strictEqual(toggleOn.sleep, false)

const sleepOn = Model.sleepPayload(sample, "lightbar", true)
assert.strictEqual(sleepOn.sleep, true)
assert.strictEqual(sleepOn.awake, true)

assert.strictEqual(Model.brightnessPayload("high").value, "high")
assert.strictEqual(Model.modeByValue("rainbow-wave").direction, true)
assert.strictEqual(Model.modeByValue("rainbow-wave").colour, false)
assert.strictEqual(Model.modeByValue("static").colour, true)
assert.strictEqual(Model.effectOptions(["flash", "static"])[0].value, "static")
assert.strictEqual(Model.effectOptions(["flash", "static"])[1].value, "flash")
assert.strictEqual(Model.pluginFilePath("file:///home/me/aura.py"), "/home/me/aura.py")

const missing = Model.parseStatus("{nope")
assert.strictEqual(missing.available, false)
assert.ok(missing.error)

const empty = Model.parseStatus("")
assert.strictEqual(empty.ok, false)

console.log("Model.test.js ok")
