from PyQt5.QtCore import QDate

import DFTableView as dftv
import chiller_efficiency as ce

from PyQt5 import QtCore, QtGui, QtWidgets

ce.TEST  = False
class Ui_MainWindow(object):

    def __init__(self):
        self.LOADS = ['avg', 'max', 'min']#['full',

        self.chillerpairs_pixmap = QtGui.QPixmap('images/default.png')
        self.chillerpairs_pixmap = self.chillerpairs_pixmap.scaled(600, 600, QtCore.Qt.KeepAspectRatio)

    def update_graph(self):
        #if self.forecasteChB.isChecked() == False:
        self.chillerpairs_pixmap = QtGui.QPixmap('fig.png')
        self.chillerpairs_pixmap = self.chillerpairs_pixmap.scaled(600, 600, QtCore.Qt.KeepAspectRatio)
        #else:
        #self.chillerpairs_pixmap = QtGui.QPixmap('images/default.png')
        #self.chillerpairs_pixmap = self.chillerpairs_pixmap.scaled(500, 500, QtCore.Qt.KeepAspectRatio)

    def predictSchedule(self):
        self.df = None
        date = self.dateEdit.date()
        date = date.toPyDate()

        expected_load = self.LOADS[self.expectedLoadCB.currentIndex()]
        tbin = self.temperatureBinSB.value()
        hbin = self.hourBinSB.value()

        self.df = ce.estimate_schedule(date.day, date.month, date.year, expected_load=expected_load,
                                       temperatureBin=tbin, hourBin=hbin,forecaste=self.forecasteChB.isChecked())

        model = dftv.pandasModel(self.df)
        self.schedule.setModel(model)
        self.update_graph()
        self.graph.setPixmap(self.chillerpairs_pixmap)

        print(expected_load, tbin, hbin)

    def saveScheduleListener(self):

        if self.df is not None:
            date = self.dateEdit.date().toPyDate()
            date = str(date.day) + '-' + str(date.month) + '-' + str(date.year)

            filename = str('Schedule_' + date)
            self.df.to_excel(filename + '.xlsx', index=False)
        else:
            print('generate a schedule first')

    def forecasteChBListener(self):

        if self.forecasteChB.isChecked():
            self.dateEdit.setEnabled(False)
            self.hourBinSB.setEnabled(False)
            self.dateEdit.hide()
            self.label.hide()

        else:
            self.dateEdit.setEnabled(True)
            self.hourBinSB.setEnabled(True)
            self.dateEdit.show()
            self.label.show()

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1078, 666)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.hourBinSB = QtWidgets.QSpinBox(self.centralwidget)
        #self.hourBinSB.setEnabled(False)
        self.hourBinSB.setMinimum(1)
        self.hourBinSB.setMaximum(1)
        self.hourBinSB.setObjectName("hourBinSB")
        self.gridLayout.addWidget(self.hourBinSB, 0, 7, 1, 1)
        self.predict = QtWidgets.QPushButton(self.centralwidget)
        self.predict.setObjectName("predict")
        self.gridLayout.addWidget(self.predict, 0, 8, 1, 1)
        self.temperatureBinSB = QtWidgets.QSpinBox(self.centralwidget)
        self.temperatureBinSB.setMinimum(1)
        self.temperatureBinSB.setMaximum(6)
        self.temperatureBinSB.setObjectName("temperatureBinSB")
        self.gridLayout.addWidget(self.temperatureBinSB, 0, 5, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 0, 2, 1, 1)
        self.expectedLoadCB = QtWidgets.QComboBox(self.centralwidget)
        self.expectedLoadCB.setObjectName("expectedLoadCB")

        #self.expectedLoadCB.addItem("FULL")
        self.expectedLoadCB.addItem("AVG")
        self.expectedLoadCB.addItem("MAX")
        self.expectedLoadCB.addItem("MIN")

        self.gridLayout.addWidget(self.expectedLoadCB, 0, 3, 1, 1)
        #self.loadBalancingRB = QtWidgets.QRadioButton(self.centralwidget)
        #self.loadBalancingRB.setEnabled(False)
        #self.loadBalancingRB.setObjectName("loadBalancingRB")
       # self.gridLayout.addWidget(self.loadBalancingRB, 2, 0, 1, 1)

        self.forecasteChB = QtWidgets.QCheckBox(self.centralwidget)
        #self.loadBalancingRB.setEnabled(False)
        self.forecasteChB.setObjectName("forecastRB")
        self.gridLayout.addWidget(self.forecasteChB, 2, 6, 1, 1)

        #fself.gridLayout.addWidget(self.label_5, 2, 6, 1, 1)

        self.dateEdit = QtWidgets.QDateEdit(self.centralwidget)
        self.dateEdit.setMinimumDate(QtCore.QDate(2020, 1, 1))
        self.dateEdit.setObjectName("dateEdit")
        d = QDate(2018, 1, 1)
        self.dateEdit.setMinimumDate(d)
        #d2 = QDate(2021, 12, 31)
        #self.dateEdit.setMaximumDate(d2)
        self.gridLayout.addWidget(self.dateEdit, 0, 1, 1, 1)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 0, 6, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 4, 1, 1)
        self.tabschedule = QtWidgets.QTabWidget(self.centralwidget)
        self.tabschedule.setObjectName("tabschedule")
        self.scheduletab = QtWidgets.QWidget()
        self.scheduletab.setObjectName("scheduletab")
        self.label_7 = QtWidgets.QLabel(self.scheduletab)
        self.label_7.setGeometry(QtCore.QRect(20, 10, 191, 20))
        self.label_7.setObjectName("label_7")
        self.schedule = QtWidgets.QTableView(self.scheduletab)
        self.schedule.setGeometry(QtCore.QRect(20, 40, 1001, 461))
        self.schedule.setObjectName("schedule")
        self.saveSchedule = QtWidgets.QPushButton(self.scheduletab)
        self.saveSchedule.setGeometry(QtCore.QRect(900, 0, 129, 32))
        self.saveSchedule.setObjectName("saveSchedule")
        self.tabschedule.addTab(self.scheduletab, "")
        self.tabgraph = QtWidgets.QWidget()
        self.tabgraph.setObjectName("tabgraph")
        self.graph = QtWidgets.QLabel(self.tabgraph)
        self.graph.setGeometry(QtCore.QRect(30, 20, 991, 500))
        self.graph.setObjectName("graph")
        #self.nextButton = QtWidgets.QPushButton(self.tabgraph)
        #self.nextButton.setGeometry(QtCore.QRect(540, 420, 113, 32))
        #self.nextButton.setObjectName("nextButton")
        #self.previousButton = QtWidgets.QPushButton(self.tabgraph)
        #self.previousButton.setGeometry(QtCore.QRect(410, 420, 113, 32))
        #self.previousButton.setObjectName("previousButton")
        #self.savegraphButton = QtWidgets.QPushButton(self.tabgraph)
       # self.savegraphButton.setGeometry(QtCore.QRect(10, 430, 113, 32))
       # self.savegraphButton.setObjectName("savegraphButton")
        self.tabschedule.addTab(self.tabgraph, "")
        self.gridLayout.addWidget(self.tabschedule, 3, 0, 1, 9)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1078, 24))
        self.menubar.setObjectName("menubar")
        self.menuChiller_Use_Scheduler = QtWidgets.QMenu(self.menubar)
        self.menuChiller_Use_Scheduler.setTitle("")
        self.menuChiller_Use_Scheduler.setObjectName("menuChiller_Use_Scheduler")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar.addAction(self.menuChiller_Use_Scheduler.menuAction())

        ##################### listeners

        self.df = None

        self.predict.clicked.connect(self.predictSchedule)
        self.saveSchedule.clicked.connect(self.saveScheduleListener)
        self.forecasteChB.stateChanged.connect(self.forecasteChBListener)

        self.retranslateUi(MainWindow)
        self.tabschedule.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Chiller Use Scheduler"))
        self.predict.setText(_translate("MainWindow", "Predict Schedule"))
        self.label_3.setText(_translate("MainWindow", "Expected Load:"))
        #self.expectedLoadCB.setItemText(0, _translate("MainWindow", "Full", "full"))
        self.expectedLoadCB.setItemText(0, _translate("MainWindow", "Average", "avg"))
        self.expectedLoadCB.setItemText(1, _translate("MainWindow", "Maximum", "max"))
        self.expectedLoadCB.setItemText(2, _translate("MainWindow", "Minimum", "min"))
        #self.loadBalancingRB.setText(_translate("MainWindow", "Load Balancing"))
        self.forecasteChB.setText(_translate("MainWindow", "Temperature Forecasting"))
        self.label.setText(_translate("MainWindow", "Input Date:"))
        self.label_5.setText(_translate("MainWindow", "Hour Bins:"))
        self.label_4.setText(_translate("MainWindow", "Temperature Bins:"))
        self.label_7.setText(_translate("MainWindow", "Schedule"))
        self.saveSchedule.setText(_translate("MainWindow", "save schedule"))
        self.tabschedule.setTabText(self.tabschedule.indexOf(self.scheduletab), _translate("MainWindow", "Schedule"))
        self.graph.setText(_translate("MainWindow", "Graph placeholder"))
        #self.nextButton.setText(_translate("MainWindow", "Next"))
        #self.previousButton.setText(_translate("MainWindow", "Previous"))
        #self.savegraphButton.setText(_translate("MainWindow", "Save Graph"))
        self.tabschedule.setTabText(self.tabschedule.indexOf(self.tabgraph), _translate("MainWindow", "Graphs"))

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())