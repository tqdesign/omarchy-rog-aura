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

  Text {
    text: root.label
    color: Qt.darker(root.foreground, 1.4)
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
    font.bold: true
    width: Style.space(14)
    anchors.verticalCenter: parent.verticalCenter
  }

  PanelSlider {
    width: Math.max(40, root.width - Style.space(52))
    bar: root.bar
    minimum: 0
    maximum: 255
    step: 1
    integer: true
    value: root.value
    fillColor: root.fill
    onMoved: function(v) { root.moved(Math.round(v)) }
    onReleased: function(v) { root.released(Math.round(v)) }
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
