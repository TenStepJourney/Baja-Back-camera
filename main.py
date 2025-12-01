import sys
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QTimer

import numpy as np

# Initialize GStreamer
Gst.init(None)


class VideoApp:
    def __init__(self):
        self.app = QApplication([])

        self.label = QLabel("Starting camera...")
        self.label.resize(800, 600)
        self.label.show()

        # Build GStreamer pipeline
        self.pipeline = Gst.parse_launch(
            "v4l2src device=/dev/video0 ! "
            "video/x-raw,format=RGB,width=1280,height=720,framerate=30/1 ! "
            "appsink name=sink max-buffers=1 drop=true"
        )

        self.appsink = self.pipeline.get_by_name("sink")
        self.appsink.set_property("emit-signals", True)
        self.appsink.connect("new-sample", self.on_new_sample)

        self.pipeline.set_state(Gst.State.PLAYING)

        # Qt timer to process GStreamer bus
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_gst)
        self.timer.start(10)

        self.bus = self.pipeline.get_bus()

    def process_gst(self):
        msg = self.bus.timed_pop_filtered(0, Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if msg:
            print(msg)

    def on_new_sample(self, sink):
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        caps = sample.get_caps()

        arr = self.gst_buffer_to_ndarray(buf, caps)
        if arr is not None:
            h, w, ch = arr.shape
            img = QImage(arr.data, w, h, ch * w, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(img))

        return Gst.FlowReturn.OK

    def gst_buffer_to_ndarray(self, buf, caps):
        success, map_info = buf.map(Gst.MapFlags.READ)
        if not success:
            return None

        try:
            struct = caps.get_structure(0)
            w = struct.get_value("width")
            h = struct.get_value("height")
            arr = np.frombuffer(map_info.data, dtype=np.uint8).reshape((h, w, 3))
        finally:
            buf.unmap(map_info)

        return arr

    def run(self):
        self.app.exec()
        self.pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    VideoApp().run()
