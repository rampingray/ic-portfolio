import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pypm import *



class AnalyzeWindow(object):
    def setupUI(self, MainWindow):
        MainWindow.setGeometry(50, 50, 400, 450)
        MainWindow.setFixedSize(400, 450)
        MainWindow.setWindowTitle("Analytics")
        self.centralwidget = QWidget(MainWindow)
        # mainwindow.setWindowIcon(QtGui.QIcon('PhotoIcon.png'))
        self.btn = QPushButton('text', self.centralwidget)
        self.btn.move(50, 350)
        MainWindow.setCentralWidget(self.centralwidget)


class PerformanceWindow(object):
    def setupUI(self, MainWindow):
        MainWindow.setGeometry(50, 50, 400, 450)
        MainWindow.setFixedSize(400, 450)
        MainWindow.setWindowTitle("Performance")
        self.centralwidget = QWidget(MainWindow)
        self.btn = QPushButton("text2", self.centralwidget)
        self.btn.move(100, 350)
        MainWindow.setCentralWidget(self.centralwidget)

class CorrelationWindow(object):
    def setupUI(self, MainWindow):
        MainWindow.setGeometry(50, 50, 400, 450)
        MainWindow.setFixedSize(400, 450)
        MainWindow.setWindowTitle("Correlation")
        self.centralwidget = QWidget(MainWindow)
        self.btn = QPushButton("text2", self.centralwidget)
        self.btn.move(100, 350)
        MainWindow.setCentralWidget(self.centralwidget)

class ChartWindow(object):
    def setupUI(self, MainWindow):
        MainWindow.setGeometry(50, 50, 400, 450)
        MainWindow.setFixedSize(400, 450)
        MainWindow.setWindowTitle("Chart")
        self.centralwidget = QWidget(MainWindow)
        self.btn = QPushButton("text2", self.centralwidget)
        self.btn.move(100, 350)
        MainWindow.setCentralWidget(self.centralwidget)

class RatiosWindow(object):
    def setupUI(self, MainWindow):
        MainWindow.setGeometry(50, 50, 400, 450)
        MainWindow.setFixedSize(400, 450)
        MainWindow.setWindowTitle("Ratios")
        self.centralwidget = QWidget(MainWindow)
        self.btn = QPushButton("text2", self.centralwidget)
        self.btn.move(100, 350)
        MainWindow.setCentralWidget(self.centralwidget)

class LoadPortfolioWindow(object):
    def setupUI(self, MainWindow):
        MainWindow.setGeometry(50, 50, 400, 450)
        MainWindow.setFixedSize(400, 450)
        MainWindow.setWindowTitle('Load Portfolio')
        self.centralwidget = QWidget(MainWindow)

        self.browseBtn = QPushButton('Browse...')
        self.runBtn = QPushButton('Run')
        self.viewBtn = QPushButton('View')
        self.pickleBtn = QPushButton('Pickle')
        self.logText = QTextBrowser()

        self.btn = QPushButton('Analyze', self.centralwidget)
        self.btn.move(100, 300)
        self.radiotest = QRadioButton('Test', self.centralwidget)
        self.radiotest.move(250, 300)

        MainWindow.setCentralWidget(self.centralwidget)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        actionStartPerformanceWindow = QAction('Performance', self)
        actionStartPerformanceWindow.triggered.connect(self.startPerformanceWindow)
        actionStartPerformanceWindow.setEnabled(False)

        actionStartAnalyzeWindow = QAction('Analyze', self)
        actionStartAnalyzeWindow.triggered.connect(self.startAnalyzeWindow)
        actionStartAnalyzeWindow.setEnabled(False)

        actionStartCorrelationWindow = QAction('Correlation', self)
        actionStartCorrelationWindow.triggered.connect(self.startCorrelationWindow)
        actionStartCorrelationWindow.setEnabled(False)

        actionStartChartWindow = QAction('Chart', self)
        actionStartChartWindow.triggered.connect(self.startChartWindow)
        actionStartChartWindow.setEnabled(False)

        actionStartRatiosWindow = QAction('Ratios', self)
        actionStartRatiosWindow.triggered.connect(self.startRatiosWindow)
        actionStartRatiosWindow.setEnabled(False)

        actionLoadPortfolioWindow = QAction('Load Portfolio', self)
        actionLoadPortfolioWindow.triggered.connect(self.startLoadPortfolioWindow)

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('File')
        fileMenu.addActions([actionLoadPortfolioWindow])
        launchMenu = mainMenu.addMenu('Launch')
        launchMenu.addActions([actionStartPerformanceWindow, actionStartAnalyzeWindow, actionStartCorrelationWindow,
                               actionStartChartWindow, actionStartRatiosWindow])

        self.analyzeWindow = AnalyzeWindow()
        self.performanceWindow = PerformanceWindow()
        self.correlationWindow = CorrelationWindow()
        self.chartWindow = ChartWindow()
        self.ratiosWindow = RatiosWindow()
        self.loadPortfolioWindow = LoadPortfolioWindow()
        self.startLoadPortfolioWindow()

    def startPerformanceWindow(self):
        self.performanceWindow.setupUI(self)
        self.performanceWindow.btn.clicked.connect(self.startAnalyzeWindow)
        self.show()

    def startAnalyzeWindow(self):
        self.analyzeWindow.setupUI(self)
        self.analyzeWindow.btn.clicked.connect(self.startLoadPortfolioWindow)
        self.show()

    def startCorrelationWindow(self):
        self.correlationWindow.setupUI(self)
        self.correlationWindow.btn.clicked.connect(self.startAnalyzeWindow)
        self.show()

    def startChartWindow(self):
        self.chartWindow.setupUI(self)
        self.chartWindow.btn.clicked.connect(self.startAnalyzeWindow)
        self.show()

    def startRatiosWindow(self):
        self.ratiosWindow.setupUI(self)
        self.ratiosWindow.btn.clicked.connect(self.startAnalyzeWindow)
        self.show()

    def startLoadPortfolioWindow(self):
        self.loadPortfolioWindow.setupUI(self)
        self.loadPortfolioWindow.btn.clicked.connect(self.startAnalyzeWindow)
        self.show()

    def file_open(self):
        name = QFileDialog.getOpenFileName(self, 'Open File')[0]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())



'''
class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setGeometry(50,50,500,300)
        self.setWindowTitle('Portfolio Tool')
        # self.setWindowIcon(QtGui.QIcon())

        self.statusBar()
        mainMenu = self.menuBar()

        fileMenu = mainMenu.addMenu('&File')


        self.home()
        self.analyzeWindow()

    def home(self):
        grid=QGridLayout()

        btnQuit = QPushButton('Quit', self)
        btnQuit.clicked.connect(self.close_application)
        btnQuit.resize(btnQuit.minimumSizeHint())
        btnQuit.move(0, 200)

        btnFile = QPushButton('Browse...', self)
        btnFile.clicked.connect(self.file_open)
        btnFile.resize(btnQuit.minimumSizeHint())
        btnFile.move(100, 100)

        self.progress = QProgressBar(self)
        self.progress.setGeometry(200,80,250,20)

        self.show()

    def analyzeWindow(self):
        grid=QGridLayout()

        self.show()

    def file_open(self):
        name = QFileDialog.getOpenFileName(self, 'Open File')
        print('name', name,'type', type(name))

    def close_application(self):
        choice = QMessageBox.question(self, 'Closing...', 'Are you sure you want to exit?', QMessageBox.Yes | QMessageBox.No)
        if choice == QMessageBox.Yes:
            print('Goodbye')
            sys.exit()
        else:
            pass



def run():
    app = QApplication(sys.argv)
    GUI = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()
'''