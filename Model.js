var MODE_CATALOG = [
  { value: "static", label: "Static", colour: true, colour2: false, speed: false, direction: false },
  { value: "breathe", label: "Breathe", colour: true, colour2: true, speed: true, direction: false },
  { value: "rainbow-cycle", label: "Cycle", colour: false, colour2: false, speed: true, direction: false },
  { value: "rainbow-wave", label: "Wave", colour: false, colour2: false, speed: true, direction: true },
  { value: "stars", label: "Stars", colour: true, colour2: true, speed: true, direction: false },
  { value: "rain", label: "Rain", colour: false, colour2: false, speed: true, direction: false },
  { value: "highlight", label: "Highlight", colour: true, colour2: false, speed: true, direction: false },
  { value: "laser", label: "Laser", colour: true, colour2: false, speed: true, direction: false },
  { value: "ripple", label: "Ripple", colour: true, colour2: false, speed: true, direction: false },
  { value: "pulse", label: "Pulse", colour: true, colour2: false, speed: false, direction: false },
  { value: "comet", label: "Comet", colour: true, colour2: false, speed: false, direction: false },
  { value: "flash", label: "Flash", colour: true, colour2: false, speed: false, direction: false }
]

var PALETTE = [
  "ff0000",
  "ff6a00",
  "ffd000",
  "00c853",
  "00e5ff",
  "26bbd9",
  "2979ff",
  "9b26b6",
  "ff00aa",
  "ffffff"
]

var BRIGHTNESS_LABELS = [
  { value: "off", label: "Off" },
  { value: "low", label: "Low" },
  { value: "med", label: "Med" },
  { value: "high", label: "High" }
]

var SPEED_LABELS = [
  { value: "low", label: "Low" },
  { value: "med", label: "Med" },
  { value: "high", label: "High" }
]

var DIRECTION_LABELS = [
  { value: "left", label: "Left" },
  { value: "right", label: "Right" },
  { value: "up", label: "Up" },
  { value: "down", label: "Down" }
]

function emptyStatus() {
  return {
    ok: false,
    available: false,
    path: "",
    mode: "static",
    modeId: 0,
    supportedModes: MODE_CATALOG.map(function(m) { return m.value }),
    colour: "000000",
    colour2: "000000",
    speed: "med",
    direction: "right",
    brightness: "off",
    brightnessId: 0,
    supportedBrightness: ["off", "low", "med", "high"],
    zones: [],
    error: ""
  }
}

function parseStatus(raw) {
  var fallback = emptyStatus()
  var text = String(raw || "").trim()
  if (!text) {
    fallback.error = "empty status"
    return fallback
  }
  var parsed
  try {
    parsed = JSON.parse(text)
  } catch (e) {
    fallback.error = "status was not JSON"
    return fallback
  }
  if (!parsed || typeof parsed !== "object") {
    fallback.error = "status was not an object"
    return fallback
  }
  var next = emptyStatus()
  next.ok = parsed.ok === true
  next.available = parsed.available === true
  next.path = typeof parsed.path === "string" ? parsed.path : ""
  next.mode = modeByValue(parsed.mode).value
  next.modeId = clampInt(parsed.modeId, 0, 12, 0)
  next.supportedModes = filterKnownModes(parsed.supportedModes)
  next.colour = normalizeHex(parsed.colour)
  next.colour2 = normalizeHex(parsed.colour2)
  next.speed = clampEnum(parsed.speed, ["low", "med", "high"], "med")
  next.direction = clampEnum(parsed.direction, ["left", "right", "up", "down"], "right")
  next.brightness = clampEnum(parsed.brightness, ["off", "low", "med", "high"], "off")
  next.brightnessId = clampInt(parsed.brightnessId, 0, 3, 0)
  next.supportedBrightness = filterKnown(parsed.supportedBrightness, ["off", "low", "med", "high"])
  next.zones = parseZones(parsed.zones)
  next.error = typeof parsed.error === "string" && parsed.error ? parsed.error : (next.available ? "" : "Aura lighting is not available")
  return next
}

function parseZones(raw) {
  var list = Array.isArray(raw) ? raw : []
  var zones = []
  for (var i = 0; i < list.length; i++) {
    var row = list[i] || {}
    var name = String(row.name || "")
    if (!name) continue
    zones.push({
      id: clampInt(row.id, 0, 255, 0),
      name: name,
      label: String(row.label || name),
      boot: row.boot === true,
      awake: row.awake === true,
      sleep: row.sleep === true,
      shutdown: row.shutdown === true
    })
  }
  return zones
}

function filterKnown(values, allowed) {
  var out = []
  var list = Array.isArray(values) ? values : []
  for (var i = 0; i < list.length; i++) {
    var value = String(list[i] || "")
    if (allowed.indexOf(value) >= 0 && out.indexOf(value) < 0) out.push(value)
  }
  return out.length ? out : allowed.slice()
}

function filterKnownModes(values) {
  var allowed = MODE_CATALOG.map(function(m) { return m.value })
  return filterKnown(values, allowed)
}

function modeByValue(value) {
  var wanted = String(value || "")
  for (var i = 0; i < MODE_CATALOG.length; i++) {
    if (MODE_CATALOG[i].value === wanted) return MODE_CATALOG[i]
  }
  return MODE_CATALOG[0]
}

function effectOptions(supported) {
  var allowed = filterKnownModes(supported)
  var out = []
  for (var i = 0; i < MODE_CATALOG.length; i++) {
    if (allowed.indexOf(MODE_CATALOG[i].value) >= 0) out.push(MODE_CATALOG[i])
  }
  return out
}

function brightnessOptions(supported) {
  var allowed = filterKnown(supported, ["off", "low", "med", "high"])
  var out = []
  for (var i = 0; i < BRIGHTNESS_LABELS.length; i++) {
    if (allowed.indexOf(BRIGHTNESS_LABELS[i].value) >= 0) out.push(BRIGHTNESS_LABELS[i])
  }
  return out
}

function clampInt(value, min, max, fallback) {
  var n = Number(value)
  if (!isFinite(n)) return fallback
  n = Math.round(n)
  if (n < min) return min
  if (n > max) return max
  return n
}

function clampEnum(value, allowed, fallback) {
  var token = String(value || "").toLowerCase()
  return allowed.indexOf(token) >= 0 ? token : fallback
}

function normalizeHex(value) {
  var raw = String(value || "").trim().toLowerCase().replace(/^#/, "")
  if (/^[0-9a-f]{3}$/.test(raw)) {
    raw = raw[0] + raw[0] + raw[1] + raw[1] + raw[2] + raw[2]
  }
  if (/^[0-9a-f]{6}$/.test(raw)) return raw
  return "000000"
}

function hexFromRgb(r, g, b) {
  function part(n) {
    var v = clampInt(n, 0, 255, 0)
    var s = v.toString(16)
    return s.length === 1 ? "0" + s : s
  }
  return part(r) + part(g) + part(b)
}

function rgbFromHex(value) {
  var hex = normalizeHex(value)
  return {
    r: parseInt(hex.slice(0, 2), 16),
    g: parseInt(hex.slice(2, 4), 16),
    b: parseInt(hex.slice(4, 6), 16)
  }
}

function cssColor(value) {
  return "#" + normalizeHex(value)
}

function zoneByName(status, name) {
  var zones = status && Array.isArray(status.zones) ? status.zones : []
  for (var i = 0; i < zones.length; i++) {
    if (zones[i].name === name) return zones[i]
  }
  return null
}

function primaryZone(status) {
  return zoneByName(status, "lightbar") || (status && status.zones && status.zones[0]) || null
}

function isGlowing(status) {
  if (!status || status.available !== true) return false
  if (status.brightness === "off") return false
  var zone = primaryZone(status)
  if (zone) return zone.awake === true
  return true
}

function heroTitle(status) {
  if (!status || status.available !== true) return "Under glow"
  return modeByValue(status.mode).label
}

function heroDetail(status) {
  if (!status || status.available !== true) return status && status.error ? status.error : "No Aura device"
  if (status.brightness === "off") return "Brightness off"
  var zone = primaryZone(status)
  if (zone && !zone.awake) return zone.label + " is off"
  return "Live"
}

function nextMode(status) {
  var options = effectOptions(status && status.supportedModes)
  if (!options.length) return "static"
  var current = status && status.mode
  for (var i = 0; i < options.length; i++) {
    if (options[i].value === current) return options[(i + 1) % options.length].value
  }
  return options[0].value
}

function effectPayload(status, changes) {
  var next = changes || {}
  return {
    action: "effect",
    live: next.live === true,
    path: (next.path || (status && status.path) || ""),
    mode: next.mode || (status && status.mode) || "static",
    colour: normalizeHex(next.colour || (status && status.colour)),
    colour2: normalizeHex(next.colour2 || (status && status.colour2)),
    speed: clampEnum(next.speed || (status && status.speed), ["low", "med", "high"], "med"),
    direction: clampEnum(next.direction || (status && status.direction), ["left", "right", "up", "down"], "right")
  }
}

function brightnessPayload(value) {
  return { action: "brightness", value: clampEnum(value, ["off", "low", "med", "high"], "med") }
}

function powerPayload(zone, flags) {
  var next = flags || {}
  return {
    action: "power",
    zone: String(zone || ""),
    boot: next.boot === true,
    awake: next.awake === true,
    sleep: next.sleep === true,
    shutdown: next.shutdown === true
  }
}

function toggleZonePayload(status, name) {
  var zone = zoneByName(status, name)
  if (!zone) return null
  if (zone.awake) {
    return powerPayload(name, { boot: false, awake: false, sleep: false, shutdown: false })
  }
  return powerPayload(name, {
    boot: zone.boot || name === "lightbar" || name === "keyboard",
    awake: true,
    sleep: zone.sleep === true,
    shutdown: zone.shutdown === true
  })
}

function sleepPayload(status, name, sleepOn) {
  var zone = zoneByName(status, name)
  if (!zone) return null
  return powerPayload(name, {
    boot: zone.boot === true,
    awake: zone.awake === true || sleepOn === true,
    sleep: sleepOn === true,
    shutdown: zone.shutdown === true
  })
}

function pluginFilePath(url) {
  var path = String(url || "")
  if (path.indexOf("file://") === 0) path = path.substring(7)
  return path
}

if (typeof module !== "undefined") {
  module.exports = {
    MODE_CATALOG: MODE_CATALOG,
    PALETTE: PALETTE,
    BRIGHTNESS_LABELS: BRIGHTNESS_LABELS,
    SPEED_LABELS: SPEED_LABELS,
    DIRECTION_LABELS: DIRECTION_LABELS,
    emptyStatus: emptyStatus,
    parseStatus: parseStatus,
    parseZones: parseZones,
    modeByValue: modeByValue,
    effectOptions: effectOptions,
    brightnessOptions: brightnessOptions,
    normalizeHex: normalizeHex,
    hexFromRgb: hexFromRgb,
    rgbFromHex: rgbFromHex,
    cssColor: cssColor,
    zoneByName: zoneByName,
    primaryZone: primaryZone,
    isGlowing: isGlowing,
    heroTitle: heroTitle,
    heroDetail: heroDetail,
    nextMode: nextMode,
    effectPayload: effectPayload,
    brightnessPayload: brightnessPayload,
    powerPayload: powerPayload,
    toggleZonePayload: toggleZonePayload,
    sleepPayload: sleepPayload,
    pluginFilePath: pluginFilePath
  }
}
