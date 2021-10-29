import sys
import cv2

from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QAction, QStyle, QFileDialog, QDockWidget, QGraphicsItem, QGraphicsScene, QGraphicsView)
from PyQt5.QtGui import(QIcon, QImage, QPixmap, QPainter, QColor)
from PyQt5.QtCore import (pyqtSlot, QTimer, Qt)


class MainGraphicsItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.event = None

    def updateImage(self, image, event):
        self.image = image
        self.event = event

    def paint(self, painter, option, widget):
        painter.setPen(QColor('#FFFFFF'))
        painter.setBrush(Qt.white)
        painter.drawRect(self.event.rect())

        if self.image is None:
            return
        pixmap = QPixmap.fromImage(self.image)
        pixmap = pixmap.scaled(self.event.rect().width(), self.event.rect().height(), Qt.KeepAspectRatio, Qt.FastTransformation)
        painter.drawImage(0, 0, pixmap.toImage())


# メインウィンドウの構成
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.leftWidget = QDockWidget("left", self)
        self.bottomWidget = QDockWidget("bottom", self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.leftWidget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bottomWidget)

        self.graphitem = MainGraphicsItem()
        self.scene = QGraphicsScene()
        self.scene.addItem(self.graphitem)
        # QGraphicsView
        graphicView = QGraphicsView()
        graphicView.setScene(self.scene)
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(graphicView)
        self.central_widget.setLayout(layout)


        self.title = 'Visual Counter'
        self.left = 10
        self.top = 10
        self.width = 1280
        self.height = 960

        self.video = None

        # 動画のステータス
        self.speed = 1
        self.framePos = 0
        self.image = None
        self.moviePlayFlg = False
        self.imgWidth = 0
        self.imgHeight = 0
        self.frameRate = 0
        self.filename = QLabel("", self)

        self.timer = QTimer(self)
        self.i = 0
        self.initUI()
        self.show()

    def initUI(self):
        # メインウィンドウのタイトルを設定する
        self.setWindowTitle(self.title)
        # メインウィンドウの初期位置
        self.setGeometry(self.left, self.top, self.width, self.height)
        hbox = QHBoxLayout(self)

        # メインウィンドウのメニューを設定する
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('File')
        controlMenu = mainMenu.addMenu('Control')
        optionMenu = mainMenu.addMenu('Option')
        helpMenu = mainMenu.addMenu('Help')

        # ファイルを開くメニューを設定する
        fileOpenButton = QAction(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogStart')), 'File Open', self)
        fileOpenButton.setShortcut('Ctrl+O')
        fileOpenButton.triggered.connect(self.openFileDialog)
        fileMenu.addAction(fileOpenButton)

        # アプリの終了メニューを設定する
        exitButton = QAction(self.style().standardIcon(getattr(QStyle, 'SP_DialogCloseButton')), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.closing)
        fileMenu.addAction(exitButton)

        # 動画の再生ボタンを設定する
        moviePlayBtn = QPushButton(self.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')), 'Play', self)
        moviePlayBtn.clicked.connect(self.moviePlay)
        moviePlayMenu = QAction(self.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')), 'Play', self)
        moviePlayMenu.setShortcut('Ctrl+R')
        moviePlayMenu.triggered.connect(self.moviePlay)
        controlMenu.addAction(moviePlayMenu)


        # 動画の停止ボタンを設定する
        movieStopBtn = QPushButton(self.style().standardIcon(getattr(QStyle, 'SP_MediaPause')), 'Pause', self)
        movieStopBtn.clicked.connect(self.movieStop)
        movieStopMenu = QAction(self.style().standardIcon(getattr(QStyle, 'SP_MediaPause')), 'Pause', self)
        movieStopMenu.setShortcut('Ctrl+P')
        movieStopMenu.triggered.connect(self.movieStop)
        controlMenu.addAction(movieStopMenu)

        # 動画のバックステップボタンを設定する
        movieBackSkipBtn = QPushButton(self.style().standardIcon(getattr(QStyle, 'SP_MediaSkipBackward')), 'Back Skip', self)
        movieBackSkipBtn.clicked.connect(self.movieBackSkip)
        movieBackSkipMenu = QAction(self.style().standardIcon(getattr(QStyle, 'SP_MediaSkipBackward')), 'Back Skip', self)
        movieBackSkipMenu.setShortcut('Ctrl+Left')
        movieBackSkipMenu.triggered.connect(self.movieBackSkip)
        controlMenu.insertSeparator(movieBackSkipMenu)
        controlMenu.addAction(movieBackSkipMenu)

        # 動画の巻き戻しボタンを設定する
        movieBackBtn = QPushButton(self.style().standardIcon(getattr(QStyle, 'SP_MediaSeekBackward')), 'Back Seek', self)
        movieBackBtn.clicked.connect(self.movieBack)
        movieBackMenu = QAction(self.style().standardIcon(getattr(QStyle, 'SP_MediaSeekBackward')), 'Back Seek', self)
        movieBackMenu.setShortcut('Ctrl+<')
        movieBackMenu.triggered.connect(self.movieBack)
        controlMenu.addAction(movieBackMenu)

        self.statusBar().addWidget(moviePlayBtn)
        self.statusBar().addWidget(movieStopBtn)
        self.statusBar().addWidget(movieBackSkipBtn)
        self.statusBar().addWidget(movieBackBtn)

        # 描画更新用タイマー
        self.updateTimer = QTimer(self)
        self.updateTimer.timeout.connect(self.showNextFrame)

        self.statusBar().addWidget(self.filename)

        self.setLayout(hbox)

    def moviePlay(self):
        if self.frameRate < 1:
            return
        self.moviePlayFlg = True
        self.speed = 1
        self.updateTimer.start((1/self.frameRate) * 1000)

    def movieStop(self):
        self.moviePlayFlg = False
        self.speed = 0
        self.updateTimer.stop()

    def movieBack(self):
        if self.frameRate < 1:
            return
        self.moviePlayFlg = True
        self.speed = -1
        self.updateTimer.start((1 / self.frameRate) * 1000)

    def movieBackSkip(self):
        if self.framePos > 10:
            self.framePos -= 10
        else:
            self.framePos = 0
        self.get_image()
        self.update()

    def showNextFrame(self):
        # if self.moviePlayFlg == False:
        #     return

        self.framePos += self.speed
        if self.framePos < 0:
            self.framePos = 0
            self.movieStop()
        elif self.framePos > self.frameNum - 1:
            self.framePos = self.frameNum - 1
            self.movieStop()
        self.get_image()
        self.update()

    def get_image(self):
        # OpenCVで動画の再生フレーム位置を設定する
        self.video.set(cv2.CAP_PROP_POS_FRAMES, self.framePos)
        ret, frame = self.video.read()
        if frame is None:
            print("cannot open file")
            return False
        # 再生フレームをOpenCV形式からPyQtのQImageに変換する
        self.image = self.openCV2Qimage(frame)
        return True

    def openFileDialog(self):
        options = QFileDialog.Options()
        inputFileName, _ = QFileDialog.getOpenFileName(self, 'Open File', '',
                                                       'Movie files(*.avi *.wmv *.mp4 *.AVI *.WMV *.MP4);; All Files(*)',
                                                       options=options)
        if inputFileName is "":
            print("cancel")
            return

        # デバッグ用にステータスバーにファイル名を表示する
        self.filename.setText(inputFileName)

        # OpenCVで動画を読み込む
        if self.video is not None and self.video.isOpened():
            self.video.release()
        self.video = cv2.VideoCapture(inputFileName)

        # 最初のフレームを表示する
        self.framePos = 0
        self.video.set(cv2.CAP_PROP_POS_FRAMES, self.framePos)

        # フレーム数を取得
        self.frameNum = self.video.get(cv2.CAP_PROP_FRAME_COUNT)
        print('movie frameNum: ', str(self.frameNum))
        # フレームレートを取得
        self.frameRate = self.video.get(cv2.CAP_PROP_FPS)
        print('movie frameRate: ', str(self.frameRate))

        if not self.get_image():
            self.image = None
            self.update()
            return
        print('convert openCV to QImage')
        self.imgWidth = self.image.width()
        self.imgHeith = self.image.height()
        print('movie properties read success')

        self.update()

    def openCV2Qimage(self, cvImage):
        height, width, channel = cvImage.shape
        bytesPerLine = channel * width
        cvImageRGB = cv2.cvtColor(cvImage, cv2.COLOR_BGR2RGB)
        image = QImage(cvImageRGB, width, height, bytesPerLine, QImage.Format_RGB888)

        return image

    def paintEvent(self, event):
        self.graphitem.updateImage(self.image, event)
        self.central_widget.update()

    def closing(self):
        self.video.release()
        self.close()

    def keyPressEvent(self, key):
        k = key.key()
        if k == 32:
            if self.moviePlayFlg:
                self.movieStop()
            else:
                self.moviePlay()


def main():
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()