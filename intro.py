import sys
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QCoreApplication
import os
import win32gui, win32console

class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setupUI(self)
        # self.setGeometry(0, 0, 1366, 768)

        self.setWindowIcon((QtGui.QIcon('icon1.png')))
        self.setStyleSheet("background-color : rgb(248, 249, 251);")
        self.move(43,24)


    def setupUI(self, QWidget):
        # self.center()
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        exit_btn = QtWidgets.QPushButton(' ', self)
        exit_btn.resize(exit_btn.sizeHint())

        exit_btn.setGeometry(QtCore.QRect(1194, 50, 36, 36))
        exit_btn.setStyleSheet("border-radius : 20;")
        exit_btn.setStyleSheet(
            '''
            QPushButton{image:url(./image/icon/exit.png); border:0px;}
            QPushButton:hover{image:url(./image/icon/exit_hover.png); border:0px;}
            ''')
        exit_btn.setObjectName("pushButton_10")
        exit_btn.clicked.connect(QCoreApplication.instance().quit)

        # frame set
        self.frame = QtWidgets.QFrame(self)
        self.frame.setGeometry(QtCore.QRect(100, 100, 1080, 520))
        self.frame.setAutoFillBackground(False)
        self.frame.setStyleSheet("background-color : rgba(0, 0, 0, 0%); border-radius: 30px;")
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")

        # Button 1 : Lite Version
        self.lite_Button = QtWidgets.QPushButton(self.frame)
        self.lite_Button.setGeometry(QtCore.QRect(0, 0, 510, 520))
        self.lite_Button.setStyleSheet(
            '''
            QPushButton{
                color: white;
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                stop:0 rgba(0, 160, 182, 255),
                stop:1 rgba(144, 61, 167, 255));
                border-radius: 30px;
                image:url(./image/intro/lite.png);
                padding-top: 50px;
            }
            QPushButton:hover {
                background-color: rgb(20, 180, 202); border-radius: 30px;
            }
            ''')
        self.lite_Button.setObjectName("lite_Button")
        self.lite_Button.clicked.connect(self.lite)

        # Button 2 : Full Version
        self.full_Button = QtWidgets.QPushButton(self.frame)
        self.full_Button.setGeometry(QtCore.QRect(570, 0, 510, 520))
        self.full_Button.setStyleSheet(
            '''
            QPushButton{
                color: white;
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                stop:0 rgba(226, 0, 46, 255),
                stop:1 rgba(144, 61, 167, 255));
                border-radius: 30px;
                image:url(./image/intro/pro.png);
                padding-top: 50px;
            }
            QPushButton:hover {
                background-color: rgb(246, 20, 66); border-radius: 30px;
            }
            ''')
        self.full_Button.setObjectName("full_Button")
        self.full_Button.clicked.connect(self.full)


        # self.logo = QtWidgets.QLabel('Motion Presentation', QWidget)
        # self.logo.setGeometry(QtCore.QRect(198, 49, 213, 34))  #
        #
        # self.logo.setStyleSheet("color : rgb(32, 36, 47);");



        self.label = QtWidgets.QLabel('※ 처음 사용자 모드를 이용하면 일부 기능이 제한됩니다.', QWidget)
        self.label.setGeometry(QtCore.QRect(100, 650, 500, 34))  #

        self.label.setStyleSheet("color : rgb(32, 36, 47);");


        font = QtGui.QFont()
        font.setFamily("서울남산 장체B")
        font.setPointSize(14)
        self.label.setFont(font)
        # self.logo.setFont(font)


        self.setWindowTitle('Motion Presentation Intro')

        self.resize(1280, 720)

        self.show()

    def lite(self):
        print('lite')
        os.system('''start gesture_detection_lite.bat''')
        sys.exit()

    def full(self):
        print('full')
        os.system('''start gesture_detection.bat''')
        sys.exit()


if __name__ == '__main__':
    win32gui.ShowWindow(win32console.GetConsoleWindow(), 0)
    os.system('start ZoomIt.exe')
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())