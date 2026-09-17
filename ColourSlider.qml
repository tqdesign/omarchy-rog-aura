import QtQuick
import qs.Commons
import qs.Ui

Row {
  id: root

  property string label: "R"
  property int value: 0
  property color fill: "#888"
  property var bar: null
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family

  signal moved(int value)
  signal released(int value)

  spacing: Style.space(8)

  function valueFromX(x) {
    var w = Math.max(1, track.width)
    var raw = Math.round(255 * Math.max(0, Math.min(1, x / w)))
    return raw
  }

  Text {
    text: root.label
    color: Qt.darker(root.foreground, 1.4)
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
    font.bold: true
    width: Style.space(14)
    anchors.verticalCenter: parent.verticalCenter
  }

  Item {
    id: trackWrap
    width: Math.max(40, root.width - Style.space(52))
    height: Math.max(Style.space(22), Style.space(18))
    anchors.verticalCenter: parent.verticalCenter

    Rectangle {
      id: track
      anchors.verticalCenter: parent.verticalCenter
      anchors.left: parent.left
      anchors.right: parent.right
      height: Math.max(4, Math.round(Style.spacing.controlHeight * 0.11))
      radius: height / 2
      color: root.bar ? Style.selectedFillFor(root.bar.foreground, Color.accent) : "#333"
    }

    Rectangle {
      anchors.verticalCenter: track.verticalCenter
      anchors.left: track.left
      height: track.height
      radius: track.radius
      color: root.fill
      width: track.width * (root.value / 255)
    }

    Rectangle {
      width: Math.max(14, Math.round(Style.spacing.controlHeight * 0.38))
      height: width
      radius: width / 2
      color: root.fill
      border.width: Math.max(1, Style.space(2))
      border.color: root.bar ? root.bar.background : "#101315"
      anchors.verticalCenter: track.verticalCenter
      x: Math.max(0, Math.min(track.width - width, track.width * (root.value / 255) - width / 2))
    }

    MouseArea {
      anchors.fill: parent
      preventStealing: true
      hoverEnabled: true
      cursorShape: Qt.PointingHandCursor
      onPressed: function(mouse) { root.moved(root.valueFromX(mouse.x)) }
      onPositionChanged: function(mouse) {
        if (pressed) root.moved(root.valueFromX(mouse.x))
      }
      onReleased: function(mouse) { root.released(root.valueFromX(mouse.x)) }
    }
  }

  Text {
    text: String(root.value)
    color: root.foreground
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
    width: Style.space(28)
    horizontalAlignment: Text.AlignRight
    anchors.verticalCenter: parent.verticalCenter
  }
}
