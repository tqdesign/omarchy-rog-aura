import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

Panel {
  id: root
  moduleName: "tqdesign.rog-aura"
  ipcTarget: "tqdesign.rog-aura"
  manageIpc: false

  property var status: Model.emptyStatus()
  property var pendingPayload: null
  property bool lastApplyLive: false
  property bool draggingColour: false
  property bool draggingColour2: false
  property int red: 38
  property int green: 187
  property int blue: 217
  property int red2: 0
  property int green2: 0
  property int blue2: 0
  property string hexDraft: "26bbd9"

  readonly property string auraScript: Model.pluginFilePath(Qt.resolvedUrl("aura.py"))
  readonly property var modeInfo: Model.modeByValue(status.mode)
  readonly property var effectChoices: Model.effectOptions(status.supportedModes)
  readonly property var brightnessChoices: Model.brightnessOptions(status.supportedBrightness)
  readonly property string liveColour: Model.hexFromRgb(red, green, blue)
  readonly property color swatch: Model.cssColor(liveColour)
  readonly property color contentForeground: bar ? bar.foreground : Color.foreground
  readonly property string contentFontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property color dim: Qt.darker(contentForeground, 1.4)
  readonly property var service: {
    if (bar && bar.shell && typeof bar.shell.serviceFor === "function")
      return bar.shell.serviceFor("tqdesign.rog-aura")
    return null
  }
  readonly property bool lidClosed: (service && service.lidClosed === true) || status.lidClosed === true
  readonly property bool glowing: Model.isGlowing(status) && !root.lidClosed
  readonly property var lightbar: Model.zoneByName(status, "lightbar")
  readonly property real chipWidth: Math.max(80, Math.floor((bodyColumn.width - Style.space(16)) / 3))

  function auraCommand(args) {
    return ["python3", root.auraScript].concat(args)
  }

  function patchStatus(changes) {
    var next = JSON.parse(JSON.stringify(root.status))
    var key
    for (key in changes) next[key] = changes[key]
    root.status = next
    return next
  }

  function applyStatus(text) {
    var next = Model.parseStatus(text)
    root.status = next
    if (!root.draggingColour) {
      var rgb = Model.rgbFromHex(next.colour)
      root.red = rgb.r
      root.green = rgb.g
      root.blue = rgb.b
      root.hexDraft = next.colour
    }
    if (!root.draggingColour2) {
      var rgb2 = Model.rgbFromHex(next.colour2)
      root.red2 = rgb2.r
      root.green2 = rgb2.g
      root.blue2 = rgb2.b
    }
  }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function runApply(payload) {
    root.lastApplyLive = !!(payload && payload.live)
    applyProc.exec(auraCommand(["apply", JSON.stringify(payload)]))
  }

  function enqueueApply(payload) {
    if (!payload) return
    if (applyProc.running) {
      root.pendingPayload = payload
      return
    }
    runApply(payload)
  }

  function setMode(value) {
    var next = patchStatus({ mode: value })
    enqueueApply(Model.effectPayload(next, { mode: value }))
  }

  function setColourFromRgb() {
    var hex = Model.hexFromRgb(root.red, root.green, root.blue)
    root.hexDraft = hex
    var next = patchStatus({ colour: hex })
    enqueueApply(Model.effectPayload(next, { colour: hex, live: true }))
  }

  function setColour2FromRgb() {
    var hex = Model.hexFromRgb(root.red2, root.green2, root.blue2)
    var next = patchStatus({ colour2: hex })
    enqueueApply(Model.effectPayload(next, { colour2: hex, live: true }))
  }

  function setHexColour(text) {
    var hex = Model.normalizeHex(text)
    root.hexDraft = hex
    var rgb = Model.rgbFromHex(hex)
    root.red = rgb.r
    root.green = rgb.g
    root.blue = rgb.b
    var next = patchStatus({ colour: hex })
    enqueueApply(Model.effectPayload(next, { colour: hex, live: true }))
  }

  function setSpeed(value) {
    var next = patchStatus({ speed: value })
    enqueueApply(Model.effectPayload(next, { speed: value }))
  }

  function setDirection(value) {
    var next = patchStatus({ direction: value })
    enqueueApply(Model.effectPayload(next, { direction: value }))
  }

  function setBrightness(value) {
    patchStatus({ brightness: value })
    enqueueApply(Model.brightnessPayload(value))
  }

  function toggleZone(name) {
    var payload = Model.toggleZonePayload(root.status, name)
    if (!payload) return
    var zones = JSON.parse(JSON.stringify(root.status.zones || []))
    for (var i = 0; i < zones.length; i++) {
      if (zones[i].name === name) zones[i].awake = !zones[i].awake
    }
    patchStatus({ zones: zones })
    enqueueApply(payload)
  }

  function setLightbarSleep(sleepOn) {
    var payload = Model.sleepPayload(root.status, "lightbar", sleepOn)
    if (!payload) return
    enqueueApply(payload)
  }

  function cycleMode() {
    setMode(Model.nextMode(root.status))
  }

  function cycleBrightness(delta) {
    var options = root.brightnessChoices
    if (!options.length) return
    var idx = 0
    for (var i = 0; i < options.length; i++) {
      if (options[i].value === root.status.brightness) { idx = i; break }
    }
    var next = options[(idx + (delta > 0 ? 1 : options.length - 1)) % options.length]
    setBrightness(next.value)
  }

  Process {
    id: statusProc
    command: root.auraCommand(["status"])
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (!root.draggingColour && !applyProc.running) root.applyStatus(text)
    }
  }

  Process {
    id: applyProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (root.lastApplyLive) {
          var next = Model.parseStatus(text)
          if (next.ok && next.available) return
        }
        root.applyStatus(text)
      }
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (String(text || "").trim()) console.warn("tqdesign.rog-aura:", text)
    }
    onExited: {
      if (root.pendingPayload) {
        var payload = root.pendingPayload
        root.pendingPayload = null
        root.runApply(payload)
      }
    }
  }

  Timer {
    interval: root.opened ? 2000 : 8000
    running: true
    repeat: true
    onTriggered: if (!applyProc.running && !root.draggingColour) root.refresh()
  }

  Timer {
    id: colourDebounce
    interval: 40
    repeat: false
    onTriggered: root.setColourFromRgb()
  }

  Timer {
    id: colour2Debounce
    interval: 40
    repeat: false
    onTriggered: root.setColour2FromRgb()
  }

  Component.onCompleted: refresh()

  IpcHandler {
    target: "tqdesign.rog-aura"
    function open(): void { root.open() }
    function close(): void { root.close() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
    function toggle(): void { root.toggle() }
    function status(): string { return JSON.stringify(root.status) }
    function refresh(): void { root.refresh() }
    function setColour(hex: string): string { root.setHexColour(hex); return root.liveColour }
    function nextMode(): string { root.cycleMode(); return root.status.mode }
    function toggleLightbar(): string {
      root.toggleZone("lightbar")
      return root.lightbar && root.lightbar.awake ? "on" : "off"
    }
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    tooltipText: root.status.available
      ? (Model.heroTitle(root.status) + " · " + Model.heroDetail(root.status))
      : (root.status.error || "ROG under glow")
    iconComponent: glowIcon
    onPressed: function(b) {
      if (b === Qt.RightButton) root.toggleZone(root.lightbar ? "lightbar" : (root.status.zones[0] ? root.status.zones[0].name : ""))
      else if (b === Qt.MiddleButton) root.cycleMode()
      else root.toggle()
    }
    onWheelMoved: function(delta) { root.cycleBrightness(delta) }
  }

  Component {
    id: glowIcon
    Item {
      Rectangle {
        anchors.centerIn: parent
        width: Math.round(parent.width * 0.42)
        height: width
        radius: width / 2
        color: root.glowing ? root.swatch : "transparent"
        border.width: Math.max(1, Style.space(1))
        border.color: root.glowing ? root.swatch : root.contentForeground
        opacity: root.status.available ? 1 : 0.35

        Rectangle {
          anchors.fill: parent
          anchors.margins: -Math.round(parent.width * 0.35)
          radius: width / 2
          color: root.swatch
          opacity: root.glowing ? 0.28 : 0
        }
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(400))
    contentHeight: panel.fittedContentHeight(bodyColumn.implicitHeight, Style.space(640))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: bodyColumn.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

        Column {
          id: bodyColumn
          width: parent.width
          spacing: Style.space(12)

          PanelHero {
            width: parent.width
            foreground: root.contentForeground
            fontFamily: root.contentFontFamily
            title: Model.heroTitle(root.status)
            detail: root.lidClosed ? "Lid closed" : Model.heroDetail(root.status)
            iconComponent: laptopGlow
          }

          Text {
            visible: !root.status.available
            width: parent.width
            wrapMode: Text.WordWrap
            text: root.status.error || "asusd did not find Aura lighting on this machine."
            color: root.dim
            font.family: root.contentFontFamily
            font.pixelSize: Style.font.bodySmall
          }

          Column {
            width: parent.width
            spacing: Style.space(12)
            visible: root.status.available

            PanelSectionHeader {
              text: "ZONES"
              foreground: root.contentForeground
              fontFamily: root.contentFontFamily
            }

            Repeater {
              model: root.status.zones
              Toggle {
                width: bodyColumn.width
                label: modelData.label
                description: modelData.name === "lightbar"
                  ? "Lights under the laptop."
                  : (modelData.name === "keyboard" ? "Keyboard backlight stays in sync with the same effect." : "")
                checked: modelData.awake === true
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onClicked: root.toggleZone(modelData.name)
              }
            }

            Toggle {
              visible: !!root.lightbar
              width: parent.width
              label: "Stay on while sleeping"
              description: "Keep the under glow lit when the laptop sleeps."
              checked: root.lightbar && root.lightbar.sleep === true
              foreground: root.contentForeground
              fontFamily: root.contentFontFamily
              onClicked: root.setLightbarSleep(!(root.lightbar && root.lightbar.sleep))
            }

            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              visible: root.status.zones.length > 1
              text: "Colour and effect are shared. Use the toggles to turn each zone on or off."
              color: root.dim
              font.family: root.contentFontFamily
              font.pixelSize: Style.font.bodySmall
            }

            PanelSeparator { foreground: root.contentForeground }

            PanelSectionHeader {
              text: "BRIGHTNESS"
              foreground: root.contentForeground
              fontFamily: root.contentFontFamily
            }

            ButtonGroup {
              width: parent.width
              foreground: root.contentForeground
              fontFamily: root.contentFontFamily
              fontSize: Style.font.bodySmall
              value: root.status.brightness
              focusable: false
              options: root.brightnessChoices
              onChanged: function(v) { root.setBrightness(v) }
            }

            PanelSeparator { foreground: root.contentForeground }

            Column {
              width: parent.width
              spacing: Style.space(10)
              visible: root.modeInfo.colour

              PanelSectionHeader {
                text: root.modeInfo.colour2 ? "COLOUR 1" : "COLOUR"
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
              }

              Flow {
                width: parent.width
                spacing: Style.space(8)

                Repeater {
                  model: Model.PALETTE
                  Rectangle {
                    width: Style.space(28)
                    height: width
                    radius: width / 2
                    color: Model.cssColor(modelData)
                    border.width: Model.normalizeHex(modelData) === root.liveColour ? 2 : 1
                    border.color: Model.normalizeHex(modelData) === root.liveColour
                      ? root.contentForeground
                      : Qt.rgba(contentForeground.r, contentForeground.g, contentForeground.b, 0.35)

                    MouseArea {
                      anchors.fill: parent
                      preventStealing: true
                      hoverEnabled: true
                      cursorShape: Qt.PointingHandCursor
                      onPressed: root.setHexColour(modelData)
                    }
                  }
                }
              }

              ColourSlider {
                width: parent.width
                label: "R"
                value: root.red
                fill: "#ff5b5b"
                bar: root.bar
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onMoved: function(v) { root.draggingColour = true; root.red = v; root.hexDraft = root.liveColour; colourDebounce.restart() }
                onReleased: function(v) { root.red = v; root.draggingColour = false; root.setColourFromRgb() }
              }
              ColourSlider {
                width: parent.width
                label: "G"
                value: root.green
                fill: "#3ddc84"
                bar: root.bar
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onMoved: function(v) { root.draggingColour = true; root.green = v; root.hexDraft = root.liveColour; colourDebounce.restart() }
                onReleased: function(v) { root.green = v; root.draggingColour = false; root.setColourFromRgb() }
              }
              ColourSlider {
                width: parent.width
                label: "B"
                value: root.blue
                fill: "#4aa3ff"
                bar: root.bar
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onMoved: function(v) { root.draggingColour = true; root.blue = v; root.hexDraft = root.liveColour; colourDebounce.restart() }
                onReleased: function(v) { root.blue = v; root.draggingColour = false; root.setColourFromRgb() }
              }

              Row {
                width: parent.width
                spacing: Style.space(10)

                Rectangle {
                  width: Style.space(28)
                  height: Style.space(28)
                  radius: Style.cornerRadius
                  color: root.swatch
                  border.color: root.contentForeground
                  border.width: 1
                  anchors.verticalCenter: parent.verticalCenter
                }

                TextField {
                  width: parent.width - Style.space(38)
                  text: root.hexDraft
                  foreground: root.contentForeground
                  font.family: root.contentFontFamily
                  onEditingFinished: root.setHexColour(text)
                  onAccepted: root.setHexColour(text)
                }
              }
            }

            Column {
              width: parent.width
              spacing: Style.space(10)
              visible: root.modeInfo.colour2

              PanelSectionHeader {
                text: "COLOUR 2"
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
              }

              ColourSlider {
                width: parent.width
                label: "R"
                value: root.red2
                fill: "#ff5b5b"
                bar: root.bar
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onMoved: function(v) { root.draggingColour2 = true; root.red2 = v; colour2Debounce.restart() }
                onReleased: function(v) { root.red2 = v; root.draggingColour2 = false; root.setColour2FromRgb() }
              }
              ColourSlider {
                width: parent.width
                label: "G"
                value: root.green2
                fill: "#3ddc84"
                bar: root.bar
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onMoved: function(v) { root.draggingColour2 = true; root.green2 = v; colour2Debounce.restart() }
                onReleased: function(v) { root.green2 = v; root.draggingColour2 = false; root.setColour2FromRgb() }
              }
              ColourSlider {
                width: parent.width
                label: "B"
                value: root.blue2
                fill: "#4aa3ff"
                bar: root.bar
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                onMoved: function(v) { root.draggingColour2 = true; root.blue2 = v; colour2Debounce.restart() }
                onReleased: function(v) { root.blue2 = v; root.draggingColour2 = false; root.setColour2FromRgb() }
              }
            }

            PanelSeparator { foreground: root.contentForeground }

            PanelSectionHeader {
              text: "EFFECT"
              foreground: root.contentForeground
              fontFamily: root.contentFontFamily
            }

            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: "Cycle, Wave, Stars, and the rest are driven on the under glow. Keyboard still uses the factory Aura mode."
              color: root.dim
              font.family: root.contentFontFamily
              font.pixelSize: Style.font.bodySmall
            }

            Grid {
              id: effectGrid
              width: parent.width
              columns: 3
              columnSpacing: Style.space(8)
              rowSpacing: Style.space(8)

              Repeater {
                model: root.effectChoices
                Button {
                  width: root.chipWidth
                  text: modelData.label
                  selected: modelData.value === root.status.mode
                  foreground: root.contentForeground
                  fontFamily: root.contentFontFamily
                  fontSize: Style.font.bodySmall
                  horizontalPadding: Style.space(8)
                  onClicked: root.setMode(modelData.value)
                }
              }
            }

            Column {
              width: parent.width
              spacing: Style.space(8)
              visible: root.modeInfo.speed

              Text {
                text: "Speed"
                color: root.dim
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.bodySmall
              }

              ButtonGroup {
                width: parent.width
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                fontSize: Style.font.bodySmall
                value: root.status.speed
                focusable: false
                options: Model.SPEED_LABELS
                onChanged: function(v) { root.setSpeed(v) }
              }
            }

            Column {
              width: parent.width
              spacing: Style.space(8)
              visible: root.modeInfo.direction

              Text {
                text: "Direction"
                color: root.dim
                font.family: root.contentFontFamily
                font.pixelSize: Style.font.bodySmall
              }

              ButtonGroup {
                width: parent.width
                foreground: root.contentForeground
                fontFamily: root.contentFontFamily
                fontSize: Style.font.bodySmall
                value: root.status.direction
                focusable: false
                options: Model.DIRECTION_LABELS
                onChanged: function(v) { root.setDirection(v) }
              }
            }
          }
        }
      }
    }
  }

  Component {
    id: laptopGlow
    Item {
      implicitWidth: Style.space(44)
      implicitHeight: Style.space(36)

      Rectangle {
        id: lid
        width: parent.width * 0.86
        height: parent.height * 0.58
        radius: 3
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        color: "transparent"
        border.color: root.contentForeground
        border.width: 1
      }

      Rectangle {
        width: parent.width * 0.94
        height: parent.height * 0.18
        radius: 2
        anchors.top: lid.bottom
        anchors.topMargin: 2
        anchors.horizontalCenter: parent.horizontalCenter
        color: Qt.rgba(contentForeground.r, contentForeground.g, contentForeground.b, 0.12)
        border.color: root.contentForeground
        border.width: 1
      }

      Rectangle {
        width: parent.width * 0.9
        height: 4
        radius: 2
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        color: root.glowing ? root.swatch : Qt.rgba(contentForeground.r, contentForeground.g, contentForeground.b, 0.25)
        opacity: root.glowing ? 1 : 0.5
      }
    }
  }

}
