import QtQuick
import Quickshell
import Quickshell.Io
import "Model.js" as Model

Item {
  id: root

  property var shell: null
  property var manifest: null
  property bool lidClosed: false

  readonly property string auraScript: Model.pluginFilePath(Qt.resolvedUrl("aura.py"))

  function startWatch() {
    if (watchProc.running) return
    watchProc.running = true
  }

  Process {
    id: watchProc
    command: ["python3", "-u", root.auraScript, "watch-lid", "--apply"]
    stdout: SplitParser {
      onRead: function(line) {
        try {
          var raw = JSON.parse(String(line || ""))
          if (raw && typeof raw.closed === "boolean") root.lidClosed = raw.closed
          else if (raw && typeof raw.lidClosed === "boolean") root.lidClosed = raw.lidClosed
        } catch (e) {}
      }
    }
    stderr: StdioCollector {
      waitForEnd: false
    }
    onExited: restartWatch.restart()
  }

  Timer {
    id: restartWatch
    interval: 800
    repeat: false
    onTriggered: root.startWatch()
  }

  Component.onCompleted: startWatch()
}
