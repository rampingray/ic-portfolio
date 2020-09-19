import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pypm import *

class Window(QMainWindow):

    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(50,50,500,300)
        self.setWindowTitle('Portfolio Tool')
        # self.setWindowIcon(QtGui.QIcon())

        self.statusBar()
        mainMenu = self.menuBar()

        fileMenu = mainMenu.addMenu('&File')


        self.home()

    def home(self):
        btnQuit = QPushButton('Quit', self)
        btnQuit.clicked.connect(self.close_application)
        btnQuit.resize(btnQuit.minimumSizeHint())
        btnQuit.move(0, 100)

        btnFile = QPushButton('Browse...', self)
        btnFile.clicked.connect(self.file_open)
        btnQuit.resize(btnQuit.minimumSizeHint())
        btnQuit.move(100, 100)

        self.progress = QProgressBar(self)
        self.progress.setGeometry(200,80,250,20)

        self.show()

    def file_open(self):
        name = QFileDialog.getOpenFileName(self, 'Open File')

    def close_application(self):
        choice = QMessageBox.question(self, 'Closing...', 'Are you sure you want to exit?', QMessageBox.Yes | QMessageBox.No)
        if choice == QMessageBox.Yes:
            print('Goodbye')
            sys.exit()
        else:
            pass

def run():
    app = QApplication(sys.argv)
    GUI = Window()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()